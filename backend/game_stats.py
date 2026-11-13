# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Статистика по играм (3.4.0): рабочие уровни TDP, на которых игра держала цель FPS.

Игра определяется по процессу запуска Steam: `reaper SteamLaunch AppId=<id> -- ...`
(так запускаются и игры Steam, и добавленные ярлыки). Если такого процесса нет,
используется общий ключ 'default'.

Режим экрана (3.6.0): одна и та же игра в руках на встроенном экране и в доке на
мониторе 2K/4K требует разной мощности, поэтому уровни хранятся отдельно для каждого
режима. Режим берётся из /sys/class/drm: какие выходы включены (встроенный eDP или
внешний DP/HDMI) и их родное разрешение. Пример ключей:
    steam:1091500@handheld-1920x1080
    steam:1091500@external-2560x1440
    steam:1091500@external-3840x2160

Файл: <папка настроек плагина>/game_stats.json
    {"steam:1091500@handheld-1920x1080": {"name": "...", "levels": [35.0, 36.0], "updated": 1731400000}}
"""

import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_GAME = 'default'
MAX_GAMES = 200
_APPID_RE = re.compile(rb'AppId=(\d+)')


def detect_game(proc: Path = Path('/proc')) -> Optional[str]:
    """'steam:<AppId>' запущенной игры или None."""
    try:
        entries = os.listdir(proc)
    except OSError:
        return None
    for pid in entries:
        if not pid.isdigit():
            continue
        try:
            cmdline = (proc / pid / 'cmdline').read_bytes()
        except OSError:
            continue
        if b'SteamLaunch' not in cmdline:
            continue
        m = _APPID_RE.search(cmdline)
        if m and m.group(1) != b'0':
            return f'steam:{m.group(1).decode()}'
    return None


INTERNAL_CONNECTORS = ('eDP', 'LVDS', 'DSI')


def _connector_mode(conn: Path) -> Optional[Tuple[int, int]]:
    """Родное (первое, предпочтительное) разрешение выхода."""
    try:
        first = conn.joinpath('modes').read_text().split('\n', 1)[0].strip()
    except OSError:
        return None
    m = re.match(r'(\d+)x(\d+)', first)
    return (int(m.group(1)), int(m.group(2))) if m else None


def detect_display(drm: Path = Path('/sys/class/drm')) -> Optional[str]:
    """'handheld-<W>x<H>' или 'external-<W>x<H>' по включённым выходам, иначе None.

    Если включён хотя бы один внешний выход, режим внешний (док): игра рисует для него.
    Из нескольких внешних берётся самый большой. Текущий режим ядро в sysfs не
    показывает, поэтому используется родное разрешение экрана.
    """
    internal, external = [], []
    try:
        conns = sorted(drm.glob('card*-*'))
    except OSError:
        return None
    for conn in conns:
        name = conn.name.split('-', 1)[1] if '-' in conn.name else conn.name
        if name.startswith('Writeback'):
            continue
        try:
            if conn.joinpath('status').read_text().strip() != 'connected':
                continue
            enabled = conn.joinpath('enabled').read_text().strip() == 'enabled'
        except OSError:
            continue
        if not enabled:
            continue
        mode = _connector_mode(conn)
        if mode is None:
            continue
        (internal if name.startswith(INTERNAL_CONNECTORS) else external).append(mode)
    if external:
        w, h = max(external, key=lambda wh: wh[0] * wh[1])
        return f'external-{w}x{h}'
    if internal:
        w, h = internal[0]
        return f'handheld-{w}x{h}'
    return None


def stats_key(game: str, display: Optional[str]) -> str:
    return f'{game}@{display}' if display else game


def steam_game_name(game: str, home: Optional[Path] = None) -> Optional[str]:
    """Название из appmanifest_<id>.acf основной библиотеки Steam (если найдётся)."""
    if not game.startswith('steam:'):
        return None
    appid = game.split(':', 1)[1]
    home = home or Path(os.environ.get('DECKY_USER_HOME', '/home/deck'))
    for lib in (home / '.local/share/Steam/steamapps', home / '.steam/steam/steamapps'):
        try:
            text = (lib / f'appmanifest_{appid}.acf').read_text(errors='replace')
        except OSError:
            continue
        m = re.search(r'"name"\s+"([^"]+)"', text)
        if m:
            return m.group(1)
    return None


class GameStats:
    FILENAME = 'game_stats.json'

    def __init__(self, settings_dir):
        self.path = Path(settings_dir) / self.FILENAME if settings_dir else None
        self._lock = threading.Lock()
        self._data: Dict[str, dict] = self._load()

    def _load(self) -> Dict[str, dict]:
        if self.path is None:
            return {}
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as e:
            logger.warning('game stats unreadable, starting empty: %s', e)
            return {}
        return data if isinstance(data, dict) else {}

    def levels(self, game: str) -> List[float]:
        with self._lock:
            entry = self._data.get(game) or {}
            vals = entry.get('levels') if isinstance(entry, dict) else None
            return [float(v) for v in vals if isinstance(v, (int, float))] if isinstance(vals, list) else []

    def name(self, game: str) -> Optional[str]:
        with self._lock:
            entry = self._data.get(game)
            return entry.get('name') if isinstance(entry, dict) else None

    def name_for_game(self, game: str) -> Optional[str]:
        """Сохранённое название игры из любой её записи (в любом режиме экрана)."""
        with self._lock:
            for key, entry in self._data.items():
                if (key == game or key.startswith(game + '@')) and isinstance(entry, dict) and entry.get('name'):
                    return entry['name']
        return None

    def put_levels(self, game: str, levels: List[float], name: Optional[str] = None) -> None:
        with self._lock:
            entry = self._data.get(game) if isinstance(self._data.get(game), dict) else {}
            entry['levels'] = [round(float(v), 1) for v in levels]
            entry['updated'] = int(time.time())
            if name:
                entry['name'] = name
            self._data[game] = entry
            if len(self._data) > MAX_GAMES:
                oldest = sorted(self._data, key=lambda k: (self._data[k] or {}).get('updated', 0))
                for k in oldest[:len(self._data) - MAX_GAMES]:
                    self._data.pop(k, None)
            self._save()

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.game_stats.', suffix='.tmp', dir=str(self.path.parent))
            with os.fdopen(fd, 'w') as f:
                json.dump(self._data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as e:
            logger.warning('game stats not saved: %s', e)
