# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class TDPControllerException(Exception):
    pass

class TDPController:
    """Real TDP control for GPD Win 5 / Strix Halo.

    Backend priority:
      1. AMD DPTC firmware-attributes (when kernel exposes it).
      2. PowerControl's bundled ryzenadj (no AUR dependency).
      3. A system ryzenadj, if one is already installed.

    We never map EPP to TDP: EPP is a separate optional control.
    """
    DPTC = Path('/sys/class/firmware-attributes/amd_dptc/attributes')
    ALT_DPTC = Path('/sys/class/firmware-attributes/amd-dptc/attributes')

    def __init__(self):
        self.backend = 'none'
        self.path: Optional[Path] = None
        self.ryzenadj: Optional[str] = None
        self.min_w = 5.0
        self.max_w = 55.0
        self.current_w: Optional[float] = None
        self._detect()

    def _detect(self):
        for p in (self.DPTC, self.ALT_DPTC):
            if p.exists() and p.is_dir():
                # Both the original RFC ABI and the later firmware-attributes
                # names are supported.
                names = [
                    ('ppt_pl1_spl', 'ppt_pl2_sppt', 'ppt_pl3_fppt'),
                    ('stapm_limit', 'fast_limit', 'slow_limit'),
                ]
                for n1, n2, n3 in names:
                    if (p / n1 / 'current_value').exists():
                        self.backend = 'dptc'
                        self.path = p
                        self._read_limits(n1)
                        logger.info('TDP backend: DPTC at %s', p)
                        return

        candidates = []
        bundled = Path(__file__).resolve().parent.parent / 'bin' / 'ryzenadj'
        if bundled.is_file() and os.access(bundled, os.X_OK):
            candidates.append(bundled)
        homebrew = os.environ.get('DECKY_HOME', '/home/deck/homebrew')
        candidates += [
            Path(homebrew) / 'plugins/PowerControl/bin/ryzenadj',
            Path('/home/deck/homebrew/plugins/PowerControl/bin/ryzenadj'),
            Path('/root/homebrew/plugins/PowerControl/bin/ryzenadj'),
            Path('/usr/bin/ryzenadj'), Path('/usr/sbin/ryzenadj'),
            Path('/usr/local/bin/ryzenadj'),
        ]
        for p in candidates:
            if p.is_file() and os.access(p, os.X_OK):
                self.backend = 'ryzenadj'
                self.ryzenadj = str(p)
                logger.info('TDP backend: ryzenadj at %s', p)
                return
        logger.warning('No real TDP backend found')

    def _read_limits(self, name: str):
        try:
            mn = float((self.path / name / 'min_value').read_text().strip())
            mx = float((self.path / name / 'max_value').read_text().strip())
            # DPTC v3+ exposes W, older RFC builds expose mW.
            if mx > 1000:
                mn /= 1000.0; mx /= 1000.0
            self.min_w, self.max_w = mn, min(mx, 55.0)
        except Exception:
            self.min_w, self.max_w = 5.0, 55.0

    def available(self) -> bool:
        return self.backend != 'none'

    def _read_value(self, names) -> Optional[float]:
        if not self.path: return None
        for name in names:
            p = self.path / name / 'current_value'
            if p.exists():
                try:
                    raw = p.read_text().strip()
                    if not raw: continue
                    v = float(raw)
                    if v > 1000: v /= 1000.0
                    return v
                except Exception: pass
        return None

    def read_tdp(self) -> Optional[float]:
        if self.backend == 'dptc':
            v = self._read_value(['ppt_pl1_spl', 'stapm_limit'])
            if v is not None:
                self.current_w = v
                return v
            return self.current_w
        if self.backend == 'ryzenadj' and self.ryzenadj:
            try:
                r = subprocess.run([self.ryzenadj, '-i'], capture_output=True, text=True,
                                   timeout=2, check=False)
                import re
                m = re.search(r'STAPM LIMIT\s*[:=]\s*([0-9.]+)', r.stdout, re.I)
                if m:
                    self.current_w = float(m.group(1)); return self.current_w
            except Exception as e:
                logger.debug('ryzenadj info failed: %s', e)
        return self.current_w

    def has_hardware_readback(self) -> bool:
        return self.backend == 'dptc'

    def set_tdp(self, watts: float) -> bool:
        if not self.available():
            raise TDPControllerException('No TDP backend available')
        watts = max(self.min_w, min(self.max_w, float(watts)))
        if self.backend == 'dptc':
            return self._set_dptc(watts)
        return self._set_ryzenadj(watts)

    def _set_dptc(self, watts: float) -> bool:
        assert self.path
        # Prefer the current firmware-attributes ABI; support the original
        # DPTC RFC names as well. PL2/PL3 get a modest boost over sustained.
        groups = [
            ('ppt_pl1_spl', watts), ('ppt_pl2_sppt', min(self.max_w, watts + 10)),
            ('ppt_pl3_fppt', min(self.max_w, watts + 5)),
        ]
        if not (self.path / 'ppt_pl1_spl').exists():
            groups = [
                ('stapm_limit', watts * 1000), ('fast_limit', min(self.max_w, watts + 10) * 1000),
                ('slow_limit', min(self.max_w, watts + 5) * 1000),
            ]
        for name, value in groups:
            p = self.path / name / 'current_value'
            if not p.exists(): continue
            try: p.write_text(str(int(round(value if value > 1000 else value))))
            except OSError as e:
                raise TDPControllerException(f'DPTC write {name}: {e}')
        save = self.path / 'save_settings'
        commit = self.path / 'commit'
        # Later ABI: single writes can be applied by selecting save_settings=single.
        if save.exists():
            try:
                choices = (self.path / 'save_settings' / 'choices').read_text() if (self.path / 'save_settings' / 'choices').exists() else ''
                if 'single' in choices: save.write_text('single')
            except OSError: pass
        elif commit.exists():
            try: commit.write_text('1')
            except OSError: pass
        self.current_w = watts
        return True

    def _set_ryzenadj(self, watts: float) -> bool:
        assert self.ryzenadj
        mw = str(int(round(watts * 1000)))
        cmd = [self.ryzenadj, f'--stapm-limit={mw}', f'--fast-limit={mw}', f'--slow-limit={mw}']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4, check=False)
        if r.returncode != 0:
            raise TDPControllerException((r.stderr or r.stdout or 'ryzenadj failed').strip())
        self.current_w = watts
        return True

    def stats(self) -> Dict:
        return {
            'available': self.available(), 'backend': self.backend,
            'backend_path': str(self.path or self.ryzenadj) if (self.path or self.ryzenadj) else None,
            'current_tdp': self.read_tdp(),
            'tdp_source': 'hardware' if self.has_hardware_readback() else ('setpoint' if self.current_w is not None else None),
            'hardware_readback': self.has_hardware_readback(),
            'min_tdp': self.min_w, 'max_tdp': self.max_w,
        }
