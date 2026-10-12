# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Управление активными физическими ядрами через sysfs CPU hotplug (версия 2.1.1).

Принципы:
  * Отключаются только ЦЕЛЫЕ физические ядра (оба SMT-потока).
  * Число ядер и пары потоков читаются из /sys (possible, thread_siblings_list).
  * CPU 0 никогда не отключается.
  * Минимум оставшихся физических ядер — MIN_CORES (2).
  * Перед отключением CPU вытесняются пользовательские потоки и IRQ (core_evacuation).
  * Операция выполняется фоново; текущая стадия доступна через get_status().
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
        self.cores: List[Tuple[int, ...]] = []
        self.active_cores: Optional[int] = None
        self.last_error: Optional[str] = None
        self.proc_root = Path("/proc")
        self.irq_root = Path("/proc/irq")
        self.last_evacuation: Optional[Dict[str, Any]] = None
        # Состояние фоновой операции (для UI)
        self.op_state = "idle"          # idle | running | done | error
        self.op_stage = ""              # текст текущей стадии
        self.op_detail = ""
        self.op_result: Optional[Dict[str, Any]] = None
        self._op_thread: Optional[threading.Thread] = None
        self.on_applied = None  # callback(applied:int), задаётся из main.py
        self.available = False
        with self._lock:
            self._read_possible()
            self.restore_all()
            self._read_topology()

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
                siblings = (cpu,)
            if cpu not in siblings:
                siblings = tuple(sorted(set(siblings) | {cpu}))
            groups[siblings] = None
        self.cores = sorted(groups.keys(), key=lambda g: min(g))
        self.available = len(self.cores) > 0
        logger.info("CpuTopology: %d CPU, %d physical cores: %s",
                    len(self.possible), len(self.cores), self.cores)

    def _read_online(self, cpu: int) -> bool:
        if cpu == 0 and not (self._cpu_path(0) / "online").exists():
            return True
        try:
            return (self._cpu_path(cpu) / "online").read_text().strip() == "1"
        except OSError:
            return False

    def _set_online(self, cpu: int, value: bool) -> bool:
        if cpu == 0:
            return True
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
        with self._lock:
            failed: List[int] = []
            for cpu in self.possible:
                if cpu == 0:
                    continue
                if not self._read_online(cpu) and not self._set_online(cpu, True):
                    failed.append(cpu)
            self.active_cores = None
            return {"ok": not failed, "failed": failed}

    # ------------------------------------------------------------------
    # Фоновая операция
    # ------------------------------------------------------------------
    def _progress(self, stage: str, done: int, total: int, detail: str) -> None:
        self.op_stage = stage
        self.op_detail = f"{detail} ({done}/{total})" if total else detail

    def start_apply(self, cores: int) -> Dict[str, Any]:
        """Запускает apply в фоне. Возвращает сразу: {'started': True} или отказ."""
        with self._lock:
            if self.op_state == "running":
                return {"started": False, "error": "предыдущее изменение ещё выполняется"}
            self.op_state = "running"
            self.op_stage = "подготовка"
            self.op_detail = ""
            self.op_result = None
            self._op_thread = threading.Thread(target=self._run_apply, args=(int(cores),),
                                               daemon=True, name="CpuApply")
            self._op_thread.start()
            return {"started": True}

    def _run_apply(self, cores: int) -> None:
        try:
            res = self.apply(cores, progress=self._progress)
        except Exception as e:  # защита: фоновый поток не должен падать молча
            logger.exception("CpuTopology: apply failed")
            res = {"ok": False, "error": f"внутренняя ошибка: {e}"}
        with self._lock:
            self.op_result = res
            self.op_state = "done" if res.get("ok") else "error"
            self.op_stage = "готово" if res.get("ok") else "ошибка"
        # Конфиг пишем только при фактическом успехе, иначе после перезагрузки
        # восстановится число ядер, которое не было применено.
        if res.get("ok") and res.get("applied") is not None and self.on_applied:
            try:
                self.on_applied(int(res["applied"]))
            except Exception:
                logger.exception("CpuTopology: cannot save active_cores")

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {"state": self.op_state, "stage": self.op_stage, "detail": self.op_detail,
                    "result": self.op_result}

    # ------------------------------------------------------------------
    def apply(self, cores: int, progress=None) -> Dict[str, Any]:
        """Оставить `cores` физических ядер. Синхронная реализация (вызывается из фона)."""
        from . import core_evacuation

        def report(stage, done=0, total=0, detail=""):
            if progress:
                progress(stage, done, total, detail)

        with self._lock:
            total = len(self.cores)
            if total == 0:
                return {"ok": False, "error": "топология недоступна"}
            wanted = max(min(int(cores), total), min(self.MIN_CORES, total))
            keep = self.cores[:wanted]
            drop = self.cores[wanted:]
            keep_cpus = {c for core in keep for c in core}
            drop_cpus = {c for core in drop for c in core if c != 0}
            failed: List[int] = []

            report("включение оставляемых ядер", 0, 0, "")
            for cpu in sorted(keep_cpus):
                if cpu != 0 and not self._read_online(cpu):
                    if not self._set_online(cpu, True):
                        failed.append(cpu)

            if drop_cpus and any(self._read_online(c) for c in drop_cpus):
                report("вытеснение задач и IRQ")
                ev = core_evacuation.evacuate(drop_cpus, keep_cpus, proc=self.proc_root,
                                              irq_dir=self.irq_root, progress=report)
                self.last_evacuation = ev
                if not ev.get("ok"):
                    stuck = ev.get("stuck", [])
                    reason = ev.get("error") or f"{len(stuck)} потоков привязаны к отключаемым ядрам"
                    self.last_error = f"ядра не отключены: {reason}"
                    logger.warning("CpuTopology: %s", self.last_error)
                    return {"ok": False, "requested": cores, "applied": self.active_cores,
                            "max": total, "failed": [], "error": self.last_error,
                            "stuck": stuck[:20], "evacuation": ev}

            report("отключение ядер", 0, len(drop), "")
            for i, core in enumerate(drop, 1):
                for cpu in core:
                    if cpu != 0 and self._read_online(cpu):
                        if not self._set_online(cpu, False):
                            failed.append(cpu)
                report("отключение ядер", i, len(drop), f"ядро {core}")

            self.active_cores = wanted
            logger.info("CpuTopology: active physical cores=%d (of %d), failed=%s",
                        wanted, total, failed)
            ev = self.last_evacuation or {}
            return {"ok": not failed, "requested": cores, "applied": wanted,
                    "max": total, "failed": failed, "evacuation": ev}

    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            online_threads = sum(1 for c in self.possible if self._read_online(c))
            online_cores = sum(1 for core in self.cores if any(self._read_online(c) for c in core))
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
                "operation": self.get_status(),
            }
