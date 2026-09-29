# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import csv
import glob
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class FPSReader:
    """Read live FPS from MangoHud/mangoapp CSV logs.

    CachyOS Handheld uses gamescope + mangoapp in Game Mode. This deliberately
    does not parse the visual HUD or assume SteamOS-specific paths.
    """
    def __init__(self):
        self.session_user = os.environ.get('DECKY_USER', 'deck')
        self.log_dirs = self._dirs()
        self.path: Optional[Path] = None
        self.last_mtime = 0.0
        self.last_rows = 0
        self.last_fps: Optional[float] = None
        self.started_logging = False
        self._scan_interval = 2.0
        self._last_scan = 0.0
        self.source_stale_after = 9.0
        self._known_files = {}
        self._maybe_start_logging()

    def _dirs(self) -> List[Path]:
        home = Path(os.environ.get('DECKY_USER_HOME', '/home/deck'))
        xdg = os.environ.get('XDG_DOWNLOAD_DIR')
        return [p for p in [
            home, home / 'Downloads/mango-logs', home / 'Documents/MangoLogs',
            home / '.config/MangoHud', Path('/tmp/mango-logs'),
            Path(xdg) / 'mango-logs' if xdg else None,
        ] if p]

    def _maybe_start_logging(self):
        ctl = self._find_ctl()
        if not ctl: return
        try:
            # mangoapp's control interface. If no mangoapp is running this is
            # harmlessly ignored; the reader will report no FPS instead of 0.
            r = subprocess.run([ctl, 'set', 'log_session', 'true'], capture_output=True,
                               text=True, timeout=2, check=False)
            if r.returncode == 0:
                self.started_logging = True
        except Exception as e: logger.debug('mangohudctl unavailable: %s', e)

    def _find_ctl(self) -> Optional[str]:
        for p in ['/usr/bin/mangohudctl', '/usr/local/bin/mangohudctl']:
            if os.path.isfile(p) and os.access(p, os.X_OK): return p
        return None

    def _latest(self) -> Optional[Path]:
        """Return the newest live MangoHud/mangoapp CSV.

        Mangoapp creates a new timestamped CSV when logging is restarted.
        Therefore the source is deliberately re-scanned periodically instead
        of keeping the first CSV forever.
        """
        now = time.time()
        if self._known_files and now - self._last_scan < self._scan_interval:
            p = self.path
            if p is not None and p.exists():
                return p
        self._last_scan = now

        files=[]
        home = Path(os.environ.get('DECKY_USER_HOME', '/home/deck'))
        for d in self.log_dirs:
            if not d.exists():
                continue
            if d == home:
                files += [Path(x) for x in glob.glob(str(d / 'mangoapp_*.csv'))]
            else:
                files += [Path(x) for x in glob.glob(str(d / '*.csv'))]
        files = [p for p in files if not p.name.endswith('_summary.csv')]
        if not files:
            self._known_files = {}
            return None

        current = {}
        for p in files:
            try:
                current[str(p)] = p.stat().st_mtime_ns
            except OSError:
                continue
        self._known_files = current
        if not current:
            return None
        return max((Path(x) for x in current), key=lambda x: current[str(x)])

    @staticmethod
    def _fps_values(path: Path) -> List[float]:
        # CachyOS mangoapp CSVs have two header rows: a system-info row
        # followed by the actual frame-metrics header beginning with `fps`.
        # DictReader on the first row therefore loses the real `fps` column.
        with path.open('r', newline='', errors='replace') as f:
            rows = list(csv.reader(f))

        header_idx = None
        for i, row in enumerate(rows[:10]):
            cells = [str(x).strip().lower() for x in row]
            if 'fps' in cells and ('frametime' in cells or 'cpu_load' in cells):
                header_idx = i
                break

        vals=[]
        if header_idx is not None:
            header = rows[header_idx]
            try:
                fps_idx = next(i for i, x in enumerate(header) if str(x).strip().lower() == 'fps')
            except StopIteration:
                return vals
            for row in rows[header_idx + 1:]:
                if fps_idx >= len(row):
                    continue
                raw = str(row[fps_idx]).strip()
                try:
                    vals.append(float(raw))
                except ValueError:
                    pass
            return vals

        # Fallback for conventional one-header MangoHud CSVs.
        if not rows:
            return vals
        header = [str(x).strip() for x in rows[0]]
        keys = {k.lower(): i for i, k in enumerate(header)}
        fps_idx = next((keys[k] for k in ('fps', 'fps_avg', 'avg_fps') if k in keys), None)
        if fps_idx is None:
            return vals
        for row in rows[1:]:
            if fps_idx >= len(row):
                continue
            try:
                vals.append(float(str(row[fps_idx]).strip()))
            except ValueError:
                pass
        return vals

    def read(self) -> Optional[float]:
        p = self._latest()
        if not p: return None
        try:
            stat = p.stat()
            mtime = stat.st_mtime
            # A stopped/restarted MangoHud session can leave the previous CSV
            # perfectly readable forever. Never keep reporting its last FPS
            # after the source stopped updating.
            if time.time() - mtime > self.source_stale_after:
                if p != self.path:
                    logger.info('MangoHud CSV source is stale: %s', p)
                return None

            if p != self.path:
                logger.info('MangoHud CSV source changed: %s -> %s', self.path, p)
                self.last_fps = None
                self.last_rows = 0
            self.path = p; self.last_mtime = mtime
            vals = self._fps_values(p)
            vals=[v for v in vals if 0 < v < 1000]
            if not vals: return None
            self.last_rows = len(vals)
            self.last_fps = sum(vals[-30:]) / min(30, len(vals))
            return self.last_fps
        except Exception as e:
            logger.debug('FPS CSV read failed: %s', e)
            return None

    def stats(self) -> Dict:
        return {'available': self._latest() is not None, 'fps': self.read(),
                'source': str(self.path) if self.path else None,
                'logging_started_by_plugin': self.started_logging}
