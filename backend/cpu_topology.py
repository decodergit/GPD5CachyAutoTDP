# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Управление активными физическими ядрами через sysfs CPU hotplug.

Принципы:
  * Отключаются только ЦЕЛЫЕ физические ядра (оба SMT-потока), поэтому
    гипертрединг сохраняется для всех оставшихся ядер.
  * Число ядер и пары потоков НЕ хардкодятся: читаются из
    /sys/devices/system/cpu/possible и topology/thread_siblings_list.
  * CPU 0 никогда не отключается.
  * Минимум оставшихся физических ядер — MIN_CORES (2).
  * Перед чтением топологии все CPU возвращаются онлайн, иначе после
    предыдущего сбоя плагина часть siblings могла бы не читаться.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SYSFS_CPU = Path("/sys/devices/system/cpu")


def parse_cpu_list(text: str) -> List[int]:
    """'0-3,8,10-11' -> [0,1,2,3,8,10,11]."""
    result: List[int] = []
    for part in text.strip().split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


class CpuTopology:
    MIN_CORES = 2

    def __init__(self, root: Path = SYSFS_CPU):
        self.root = Path(root)
        self._lock = threading.RLock()
        self.possible: List[int] = []
        self.cores: List[Tuple[int, ...]] = []   # физические ядра, отсортированы по первому CPU
        self.active_cores: Optional[int] = None
        self.last_error: Optional[str] = None
        self.available = False
        with self._lock:
            self._read_possible()
            # Все CPU онлайн перед чтением топологии: иначе siblings могут быть неполными.
            self.restore_all()
            self._read_topology()

    # ------------------------------------------------------------------
    # Чтение состояния системы
    # ------------------------------------------------------------------
    def _cpu_path(self, cpu: int) -> Path:
        return self.root / f"cpu{cpu}"

    def _read_possible(self) -> None:
        try:
            self.possible = parse_cpu_list((self.root / "possible").read_text())
        except (OSError, ValueError) as e:
            self.last_error = f"cannot read possible CPUs: {e}"
            logger.error("CpuTopology: %s", self.last_error)
            self.possible = []

    def _read_topology(self) -> None:
        groups: Dict[Tuple[int, ...], None] = {}
        for cpu in self.possible:
            sib_file = self._cpu_path(cpu) / "topology" / "thread_siblings_list"
            try:
                siblings = tuple(parse_cpu_list(sib_file.read_text()))
            except (OSError, ValueError):
                siblings = (cpu,)  # нет данных о SMT — считаем ядро одиночным
            if cpu not in siblings:
                siblings = tuple(sorted(set(siblings) | {cpu}))
            groups[siblings] = None
        self.cores = sorted(groups.keys(), key=lambda g: min(g))
        self.available = len(self.cores) > 0
        logger.info("CpuTopology: %d CPU, %d physical cores: %s",
                    len(self.possible), len(self.cores), self.cores)

    def _read_online(self, cpu: int) -> bool:
        if cpu == 0 and not (self._cpu_path(0) / "online").exists():
            return True  # на части систем CPU 0 не имеет файла online и всегда активен
        try:
            return (self._cpu_path(cpu) / "online").read_text().strip() == "1"
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Запись состояния
    # ------------------------------------------------------------------
    def _set_online(self, cpu: int, value: bool) -> bool:
        if cpu == 0:
            return True  # CPU 0 не трогаем
        path = self._cpu_path(cpu) / "online"
        if not path.exists():
            return False
        try:
            with open(path, "w") as f:
                f.write("1" if value else "0")
            return True
        except OSError as e:
            self.last_error = f"cpu{cpu} online={int(value)}: {e}"
            logger.warning("CpuTopology: %s", self.last_error)
            return False

    def restore_all(self) -> Dict[str, Any]:
        """Все возможные CPU онлайн. Используется при старте и выгрузке."""
        with self._lock:
            failed: List[int] = []
            for cpu in self.possible:
                if cpu == 0:
                    continue
                if not self._read_online(cpu):
                    if not self._set_online(cpu, True):
                        failed.append(cpu)
            self.active_cores = None
            return {"ok": not failed, "failed": failed}

    def apply(self, cores: int) -> Dict[str, Any]:
        """Оставить `cores` физических ядер (целыми парами SMT)."""
        with self._lock:
            total = len(self.cores)
            if total == 0:
                return {"ok": False, "error": "topology not available"}
            wanted = max(min(int(cores), total), min(self.MIN_CORES, total))
            keep = self.cores[:wanted]
            drop = self.cores[wanted:]
            keep_cpus = {c for core in keep for c in core}
            failed: List[int] = []
            # сначала включаем оставляемые, потом отключаем лишние
            for cpu in sorted(keep_cpus):
                if cpu != 0 and not self._read_online(cpu):
                    if not self._set_online(cpu, True):
                        failed.append(cpu)
            for core in drop:
                for cpu in core:
                    if cpu != 0 and self._read_online(cpu):
                        if not self._set_online(cpu, False):
                            failed.append(cpu)
            self.active_cores = wanted
            logger.info("CpuTopology: active physical cores=%d (of %d), failed=%s",
                        wanted, total, failed)
            return {"ok": not failed, "requested": cores, "applied": wanted,
                    "max": total, "failed": failed}

    # ------------------------------------------------------------------
    # Данные для UI
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            online_threads = sum(1 for c in self.possible if self._read_online(c))
            online_cores = sum(1 for core in self.cores
                               if any(self._read_online(c) for c in core))
            return {
                "available": self.available,
                "max_cores": len(self.cores),
                "min_cores": min(self.MIN_CORES, len(self.cores)),
                "active_cores": self.active_cores if self.active_cores is not None else len(self.cores),
                "online_cores": online_cores,
                "total_threads": len(self.possible),
                "online_threads": online_threads,
                "smt": any(len(core) > 1 for core in self.cores),
                "error": self.last_error,
            }
