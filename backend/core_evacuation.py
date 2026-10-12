# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Вытеснение задач и IRQ с ядер, которые собираются отключить (версия 2.1.1).

Порядок безопасного отключения набора CPU:
  1. keep = CPU, которые останутся онлайн.
  2. IRQ с отключаемых CPU переносятся на keep (/proc/irq/N/smp_affinity_list).
     Ошибка записи в IRQ НЕ блокирует отключение: часть IRQ управляется ядром
     (managed IRQ) и ядро переносит их само при offline. Такие IRQ только учитываются.
  3. Пользовательские потоки с отключаемых CPU переносятся на keep через sched_setaffinity.
     Поток, который уже завершился (ESRCH), пропускается. Поток, привязанный только
     к отключаемым CPU, блокирует отключение: его нельзя перенести без потери привязки.
  4. Только если блокирующих потоков нет, CPU отключаются.

Ядерные потоки (ksoftirqd, kworker, pid 0/2 и потомки kthreadd) не переносятся:
они привязаны к одному CPU, и ядро переносит их само.
"""

import errno
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

PROC = Path("/proc")
IRQ_DIR = Path("/proc/irq")

ProgressFn = Optional[Callable[[str, int, int, str], None]]


def _parse(text: str) -> Set[int]:
    from .cpu_topology import parse_cpu_list
    return set(parse_cpu_list(text))


def _read_affinity_list(path: Path) -> Optional[Set[int]]:
    try:
        return _parse(path.read_text())
    except (OSError, ValueError):
        return None


def _is_kernel_thread(entry: Path) -> bool:
    """entry — каталог процесса (/proc/<pid>) или потока (/proc/<pid>/task/<tid>)."""
    try:
        owner = entry.parent.parent if entry.parent.name == "task" else entry
        ppid = None
        for line in (entry / "status").read_text().splitlines():
            if line.startswith("PPid:"):
                ppid = int(line.split(":", 1)[1])
                break
        if ppid in (0, 2) or int(entry.name) in (0, 2):
            return True
        return (owner / "cmdline").read_bytes() == b""
    except (OSError, ValueError):
        return True


def list_user_threads(proc: Path = PROC) -> List[Dict[str, Any]]:
    """Пользовательские потоки: tid, pid, cpus_allowed (set), comm."""
    result: List[Dict[str, Any]] = []
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit() or _is_kernel_thread(pid_dir):
            continue
        task_dir = pid_dir / "task"
        try:
            tids = list(task_dir.iterdir())
        except OSError:
            continue
        for tid_dir in tids:
            if not tid_dir.name.isdigit() or _is_kernel_thread(tid_dir):
                continue
            try:
                status = (tid_dir / "status").read_text()
            except OSError:
                continue
            allowed = None
            comm = ""
            for line in status.splitlines():
                if line.startswith("Cpus_allowed_list:"):
                    allowed = _parse(line.split(":", 1)[1])
                elif line.startswith("Name:"):
                    comm = line.split(":", 1)[1].strip()
            if allowed is None:
                continue
            result.append({"tid": int(tid_dir.name), "pid": int(pid_dir.name),
                           "cpus_allowed": allowed, "comm": comm})
    return result


def threads_on_cpus(cpus: Iterable[int], threads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    target = set(cpus)
    return [t for t in threads if t["cpus_allowed"] & target]


def move_thread(tid: int, keep: Set[int]):
    """True — перенесён; "gone" — поток уже завершился; False — ошибка."""
    try:
        os.sched_setaffinity(tid, keep)
        return True
    except ProcessLookupError:
        return "gone"
    except (OSError, ValueError) as e:
        if getattr(e, "errno", None) == errno.ESRCH:
            return "gone"
        logger.warning("evacuate: cannot move tid %s to %s: %s", tid, sorted(keep), e)
        return False


def move_irqs(evict: Set[int], keep: Set[int], irq_dir: Path = IRQ_DIR,
              progress: ProgressFn = None) -> Dict[str, Any]:
    """Переносит IRQ с evict на keep. Ошибки не фатальны: возвращаются списком."""
    moved, skipped = 0, []
    target = ",".join(str(c) for c in sorted(keep))
    if not irq_dir.exists():
        return {"moved": 0, "skipped": [], "failed": [], "note": "no /proc/irq"}
    candidates = []
    for irq in irq_dir.iterdir():
        if not irq.name.isdigit():
            continue
        f = irq / "smp_affinity_list"
        cur = _read_affinity_list(f)
        if cur and (cur & evict):
            candidates.append((irq.name, f))
    for i, (name, f) in enumerate(candidates, 1):
        if progress:
            progress("irq", i, len(candidates), f"IRQ {name}")
        try:
            f.write_text(target)
            moved += 1
        except OSError as e:
            skipped.append(f"irq{name}: {e.strerror or e}")
    return {"moved": moved, "skipped": skipped, "failed": []}


def evacuate(evict: Iterable[int], keep: Iterable[int],
             proc: Path = PROC, irq_dir: Path = IRQ_DIR,
             progress: ProgressFn = None) -> Dict[str, Any]:
    """Полное вытеснение.

    ok = True, если нет застрявших потоков. Ошибки IRQ не влияют на ok.
    stuck — потоки, которые мешают отключению (с причиной).
    """
    evict = set(evict); keep = set(keep)
    if not keep:
        return {"ok": False, "error": "не осталось ядер для переноса (keep пуст)"}
    if evict & keep:
        return {"ok": False, "error": "внутренняя ошибка: отключаемые и оставляемые CPU пересекаются"}
    irq = move_irqs(evict, keep, irq_dir, progress)
    threads = threads_on_cpus(evict, list_user_threads(proc))
    moved, gone, stuck = 0, 0, []
    for i, t in enumerate(threads, 1):
        if progress:
            progress("threads", i, len(threads), t["comm"])
        new_mask = t["cpus_allowed"] & keep
        if not new_mask:
            stuck.append({"tid": t["tid"], "pid": t["pid"], "comm": t["comm"],
                          "reason": "привязан только к отключаемым ядрам"})
            continue
        res = move_thread(t["tid"], new_mask)
        if res is True:
            moved += 1
        elif res == "gone":
            gone += 1
        else:
            stuck.append({"tid": t["tid"], "pid": t["pid"], "comm": t["comm"],
                          "reason": "sched_setaffinity отклонён"})
    return {"ok": not stuck, "moved_threads": moved, "gone_threads": gone,
            "stuck": stuck, "irq": irq}
