# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Одноразовое восстановление CPU (версия 2.3.0).

Управление числом активных ядер удалено. Этот модуль только переводит все
процессоры в состояние online, если прошлая версия оставила часть из них отключёнными.
Ничего не отключает.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SYSFS_CPU = Path("/sys/devices/system/cpu")


def _cpu_ids(root: Path) -> list:
    ids = []
    try:
        for entry in root.iterdir():
            name = entry.name
            if name.startswith("cpu") and name[3:].isdigit():
                ids.append(int(name[3:]))
    except OSError:
        return []
    return sorted(ids)


def restore_all_cpus(root: Path = SYSFS_CPU) -> dict:
    """Включает все CPU, у которых есть файл online и значение 0. CPU 0 не трогает."""
    switched, failed = [], []
    for cpu in _cpu_ids(root):
        if cpu == 0:
            continue
        online = root / f"cpu{cpu}" / "online"
        if not online.exists():
            continue
        try:
            if online.read_text().strip() == "0":
                with open(online, "w") as f:
                    f.write("1")
                switched.append(cpu)
        except OSError as e:
            failed.append(cpu)
            logger.warning("restore_all_cpus: cpu%s: %s", cpu, e)
    if switched:
        logger.info("restore_all_cpus: switched on %s", switched)
    return {"switched": switched, "failed": failed}
