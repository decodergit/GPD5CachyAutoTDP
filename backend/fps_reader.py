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

    # Сколько байт хвоста CSV читать. Строка MangoHud ~50 байт, 64 КБ — это больше
    # 1000 последних кадров, при 10 строках/с хватает с большим запасом.
    TAIL_BYTES = 65536
    # Сколько последних значений усреднять.
    AVG_SAMPLES = 30

    @classmethod
    def _read_metrics_once(cls, path: Path, metrics: List[str]) -> Dict[str, List[float]]:
        """Читает CSV ОДИН раз и возвращает последние значения для каждой метрики.

        Раньше файл читался отдельно на каждую метрику: 3 полных чтения за опрос.
        На файле в несколько мегабайт это сотни миллисекунд, и частый опрос становился
        дороже, чем польза от него. Теперь читаются только заголовок и хвост файла.
        """
        out: Dict[str, List[float]] = {m: [] for m in metrics}
        try:
            size = path.stat().st_size
            with path.open('r', newline='', errors='replace') as f:
                # 1. Заголовок: CachyOS mangoapp пишет системную строку, затем строку метрик.
                head = f.read(4096)
                head_rows = list(csv.reader(head.splitlines()))
                header_idx = None
                header = None
                for i, row in enumerate(head_rows[:5]):
                    keys = [str(x).strip().lower() for x in row]
                    if any(m.lower() in keys for m in metrics):
                        header_idx, header = i, keys
                        break
                if header is None:
                    return out
                # 2. Хвост: только последние строки, а не весь файл.
                start = max(0, size - cls.TAIL_BYTES)
                f.seek(start)
                if start > 0:
                    f.readline()  # первая строка может быть обрезана — пропускаем
                tail = f.read()
        except (OSError, ValueError):
            return out

        idx = {}
        for m in metrics:
            try:
                idx[m] = header.index(m.lower())
            except ValueError:
                continue
        want = len(idx)
        rows = csv.reader(tail.splitlines())
        if want == 0:
            return out
        for row in rows:
            for m, i in idx.items():
                if i >= len(row):
                    continue
                try:
                    out[m].append(float(str(row[i]).strip()))
                except (ValueError, TypeError):
                    pass
        return out

    @classmethod
    def _metric_values(cls, path: Path, metric: str) -> List[float]:
        """Совместимость: значения одной метрики (используется в stats и тестах)."""
        return cls._read_metrics_once(path, [metric]).get(metric, [])

    @classmethod
    def _fps_values(cls, path: Path) -> List[float]:
        vals = cls._metric_values(path, 'fps')
        return [v for v in vals if 0 < v < 1000]

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

    def read_metrics(self) -> Dict[str, Optional[float]]:
        """Средний FPS и загрузки из живого CSV MangoHud: одно чтение файла на все метрики."""
        p = self._latest()
        if not p:
            return {'fps': None, 'cpu_load': None, 'gpu_load': None}
        try:
            if time.time() - p.stat().st_mtime > self.source_stale_after:
                return {'fps': None, 'cpu_load': None, 'gpu_load': None}
            if p != self.path:
                self.path = p
                self.last_fps = None
                self.last_rows = 0
            data = self._read_metrics_once(p, ['fps', 'cpu_load', 'gpu_load'])
            self._last_metrics = data

            def avg(metric: str, lo: float, hi: float) -> Optional[float]:
                values = [v for v in data.get(metric, []) if lo <= v <= hi]
                if not values:
                    return None
                return sum(values[-self.AVG_SAMPLES:]) / min(self.AVG_SAMPLES, len(values))

            fps = avg('fps', 0.001, 1000.0)
            cpu = avg('cpu_load', 0.0, 100.0)
            gpu = avg('gpu_load', 0.0, 100.0)
            if fps is not None:
                self.last_fps = fps
            return {'fps': fps, 'cpu_load': cpu, 'gpu_load': gpu}
        except Exception as e:
            logger.debug('MangoHud metric read failed: %s', e)
            return {'fps': None, 'cpu_load': None, 'gpu_load': None}

    def stats(self) -> Dict:
        """Без повторного чтения CSV: отдаёт результат последнего read_metrics."""
        m = getattr(self, '_last_metrics', {}) or {}

        def last(key):
            vals = list(m.get(key, []))
            return vals[-1] if vals else None

        return {'available': self._latest() is not None, 'fps': self.last_fps,
                'cpu_load': last('cpu_load'), 'gpu_load': last('gpu_load'),
                'source': str(self.path) if self.path else None,
                'logging_started_by_plugin': self.started_logging}
