# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Связь плагина Decky с настольным окном tdp_gui.py.

Оба процесса работают от root и обмениваются двумя файлами в RUN_DIR (tmpfs, /run):

  * gui.pid      — пишет окно при старте, удаляет при закрытии. Пока процесс с этим PID
                   жив и это действительно tdp_gui.py, плагин полностью приостановлен.
                   Если окно упало, PID мёртв: блокировка считается снятой.
  * plugin.json  — пишет плагин: {"pid", "active", "suspended_for"}. По нему окно узнаёт,
                   что плагин уже остановил свои циклы и можно писать TDP и вентилятор.
"""

import json
import os
from pathlib import Path
from typing import Optional

RUN_DIR = Path(os.environ.get('GPD5_AUTOTDP_RUN_DIR', '/run/gpd5cachyautotdp'))
GUI_PID_FILE = 'gui.pid'
PLUGIN_STATE_FILE = 'plugin.json'
GUI_MARKER = 'tdp_gui'


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_is_gui(pid: int) -> bool:
    """Защита от повторного использования PID: процесс должен быть tdp_gui.py."""
    try:
        cmdline = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ')
    except OSError:
        return _pid_alive(pid)  # /proc недоступен: верим проверке живости
    return GUI_MARKER.encode() in cmdline


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp.write_text(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- окно

def acquire(pid: Optional[int] = None) -> None:
    _atomic_write(RUN_DIR / GUI_PID_FILE, str(pid or os.getpid()))


def release(pid: Optional[int] = None) -> None:
    """Снимает блокировку, только если она наша."""
    path = RUN_DIR / GUI_PID_FILE
    try:
        if int(path.read_text().strip()) != (pid or os.getpid()):
            return
        path.unlink()
    except (OSError, ValueError):
        pass


def holder() -> Optional[int]:
    """PID живого окна tdp_gui.py, которое держит блокировку, иначе None."""
    try:
        pid = int((RUN_DIR / GUI_PID_FILE).read_text().strip())
    except (OSError, ValueError):
        return None
    if _pid_alive(pid) and _pid_is_gui(pid):
        return pid
    return None


# ---------------------------------------------------------------- плагин

def write_plugin_state(active: bool, suspended_for: Optional[int]) -> None:
    try:
        _atomic_write(RUN_DIR / PLUGIN_STATE_FILE, json.dumps(
            {'pid': os.getpid(), 'active': bool(active), 'suspended_for': suspended_for}))
    except OSError:
        pass


def clear_plugin_state() -> None:
    try:
        (RUN_DIR / PLUGIN_STATE_FILE).unlink()
    except OSError:
        pass


def plugin_state() -> Optional[dict]:
    """Состояние живого плагина или None (плагин не запущен или файл устарел)."""
    try:
        data = json.loads((RUN_DIR / PLUGIN_STATE_FILE).read_text())
        pid = int(data.get('pid', 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    if not _pid_alive(pid):
        return None
    return data


def plugin_released() -> bool:
    """True, если плагин не запущен или уже остановил свои циклы
    (приостановлен окном или выключен пользователем)."""
    st = plugin_state()
    if st is None:
        return True
    return not st.get('active', True)
