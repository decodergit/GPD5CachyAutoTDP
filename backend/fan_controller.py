# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Управление вентилятором GPD WIN 5 (версия 2.6.0).

Что делает цикл:
  * читает температуру как МАКСИМУМ по всем найденным датчикам (k10temp, zenpower, cpu_thermal);
  * считает целевую скважность по кривой;
  * сглаживает её: гистерезис по температуре, ограничение скорости изменения, минимум;
  * пишет в sysfs только если изменение больше мёртвой зоны.

Гистерезис: пересчёт по кривой выполняется только когда температура ушла от точки
последнего расчёта больше чем на hysteresis_c. Иначе около излома кривой вентилятор
дёргается между двумя значениями каждые 2 секунды.

Ограничение скорости: не быстрее ramp_up_pct_per_s вверх и ramp_down_pct_per_s вниз.
Убирает «взлёты» при коротком нагреве, сохраняя быструю реакцию на рост температуры.

Минимум: при включённом управлении скважность не ниже min_pct, чтобы вентилятор
не останавливался на низкой температуре.

Опережение по TDP (feed-forward): при подъёме TDP на N ватт целевая скважность
временно увеличивается на tdp_boost_pct_per_w * N на tdp_boost_sec секунд.
Температура растёт с задержкой, а вентилятор начинает раскручиваться заранее.
Обратное (снижение при падении TDP) не делается: лучше охладить лишний раз.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FanControllerException(Exception):
    pass


class FanController:
    DEFAULT_CURVE = {50: 20, 60: 25, 65: 30, 70: 35, 75: 42, 80: 55, 85: 70, 90: 85, 95: 100}

    # Параметры сглаживания (2.4.0)
    HYSTERESIS_C = 2.0            # пересчёт по кривой только при уходе температуры больше этого
    PWM_DEADBAND_PCT = 2.0        # не писать в sysfs, если изменение меньше
    RAMP_UP_PCT_PER_S = 25.0      # не быстрее этого вверх
    RAMP_DOWN_PCT_PER_S = 10.0    # и не быстрее этого вниз
    MIN_PCT = 18.0                # минимальная скважность при включённом управлении
    TDP_BOOST_PCT_PER_W = 1.5     # опережение: +1.5 % на каждый ватт подъёма TDP
    TDP_BOOST_SEC = 8.0           # сколько секунд действует опережение
    POLL_SEC = 1.0                # опрос раз в секунду, запись только при изменении

    def __init__(self):
        self.devices = []
        self.temp_paths: List[Path] = []
        self.temp_path: Optional[Path] = None
        self.curve = self.DEFAULT_CURVE.copy()
        self.enabled = False
        self._detect()
        self._stop = threading.Event()
        self._thread = None
        self.interval = self.POLL_SEC
        # Состояние сглаживания
        self._last_temp: Optional[float] = None     # температура последнего расчёта по кривой
        self._target_pct: Optional[float] = None    # целевая скважность после всех поправок
        self._applied_pct: Optional[float] = None   # фактически записанная скважность
        self._last_write_t = 0.0
        self._tdp_boost_until = 0.0
        self._tdp_boost_pct = 0.0
        self.last_error: Optional[str] = None

    # --- обнаружение ------------------------------------------------------
    def _detect(self):
        base = Path('/sys/class/hwmon')
        if not base.exists():
            return
        # Контроллер GPD авторитетен: если он есть, используем только его каналы.
        for d in sorted(base.glob('hwmon*')):
            try:
                name = (d / 'name').read_text().strip()
            except OSError as e:
                logger.debug('hwmon %s: no name: %s', d, e)
                name = ''
            pwms = [p for p in d.glob('pwm[0-9]*') if p.name[3:].isdigit()]
            if name in ('gpd_fan', 'gpd-fan', 'gpdfan') and pwms:
                self.devices = [(p, d / (p.name + '_enable')) for p in pwms]
                break
        preferred: List[Path] = []
        for d in sorted(base.glob('hwmon*')):
            try:
                name = (d / 'name').read_text().strip()
            except OSError as e:
                logger.debug('hwmon %s: no name: %s', d, e)
                name = ''
            if name in ('k10temp', 'zenpower', 'cpu_thermal'):
                preferred += sorted(d.glob('temp*_input'))
        self.temp_paths = preferred
        self.temp_path = preferred[0] if preferred else None

    def is_available(self) -> bool:
        return bool(self.devices and self.temp_paths)

    # --- измерения --------------------------------------------------------
    def read_temperature(self) -> Optional[float]:
        """Максимум по всем найденным датчикам: один датчик может врать или отставать."""
        values = []
        for p in self.temp_paths:
            try:
                values.append(int(p.read_text()) / 1000.0)
            except (OSError, ValueError):
                continue
        return max(values) if values else None

    # --- управление -------------------------------------------------------
    def _mode(self, manual: bool):
        for _, e in self.devices:
            if e.exists():
                try:
                    e.write_text('1' if manual else '2')
                except OSError as x:
                    logger.warning('fan mode: %s', x)

    def set_fan_speed(self, speed: float) -> bool:
        if not self.devices:
            return False
        pct = max(0.0, min(100.0, float(speed)))
        pwm = int(round(pct * 255 / 100))
        ok = True
        for p, _ in self.devices:
            try:
                p.write_text(str(pwm))
            except OSError as e:
                logger.warning('fan pwm: %s', e)
                ok = False
        return ok

    def calc(self, t: Optional[float]) -> float:
        """Скважность по кривой. Пустая кривая не должна выключать охлаждение."""
        pts = sorted(self.curve.items())
        if not pts:
            return 100.0
        if t is None:
            return float(pts[-1][1])
        if t <= pts[0][0]:
            return float(pts[0][1])
        if t >= pts[-1][0]:
            return float(pts[-1][1])
        for (a, sa), (b, sb) in zip(pts, pts[1:]):
            if a <= t <= b:
                return float(round(sa + (t - a) * (sb - sa) / (b - a)))
        return float(pts[-1][1])

    def note_tdp_change(self, old_w: Optional[float], new_w: Optional[float]) -> None:
        """Опережение: подъём TDP заранее поднимает целевую скважность.

        Вызывается монитором при изменении TDP. Снижение TDP опережение не включает:
        вентилятор продолжает работать по температуре.
        """
        if old_w is None or new_w is None:
            return
        delta = float(new_w) - float(old_w)
        if delta <= 0:
            return
        self._tdp_boost_pct = min(30.0, delta * self.TDP_BOOST_PCT_PER_W)
        self._tdp_boost_until = time.monotonic() + self.TDP_BOOST_SEC
        logger.debug('fan feed-forward: +%.1f%% for %.0f s (TDP +%.1f W)',
                     self._tdp_boost_pct, self.TDP_BOOST_SEC, delta)

    def _tdp_boost_now(self, now: float) -> float:
        if now < self._tdp_boost_until:
            return self._tdp_boost_pct
        return 0.0

    def compute_target(self, now: Optional[float] = None) -> Optional[float]:
        """Целевая скважность по кривой с учётом гистерезиса и опережения по TDP.

        Возвращает None, если пересчёт не требуется (температура не ушла за гистерезис).
        """
        if now is None:
            now = time.monotonic()
        t = self.read_temperature()
        if t is None:
            return None
        boost = self._tdp_boost_now(now)
        # Гистерезис: пересчитываем по кривой только при заметном уходе температуры.
        if self._last_temp is not None and boost <= 0 and abs(t - self._last_temp) < self.HYSTERESIS_C:
            base = self._target_pct if self._target_pct is not None else self.calc(t)
        else:
            self._last_temp = t
            base = self.calc(t)
        return max(self.MIN_PCT, min(100.0, base + boost))

    def smooth(self, target: float, now: Optional[float] = None) -> float:
        """Ограничение скорости изменения относительно фактически записанного значения."""
        if now is None:
            now = time.monotonic()
        if self._applied_pct is None:
            return max(self.MIN_PCT, min(100.0, target))
        dt = max(0.0, now - self._last_write_t)
        up = self.RAMP_UP_PCT_PER_S * dt
        down = self.RAMP_DOWN_PCT_PER_S * dt
        lo = self._applied_pct - down
        hi = self._applied_pct + up
        return max(self.MIN_PCT, min(100.0, min(hi, max(lo, target))))

    def apply(self, now: Optional[float] = None) -> bool:
        """Один шаг управления. Возвращает True, если значение было записано."""
        if not self.enabled:
            return False
        if now is None:
            now = time.monotonic()
        target = self.compute_target(now)
        if target is None:
            return False
        self._target_pct = target
        value = self.smooth(target, now)
        if self._applied_pct is not None and abs(value - self._applied_pct) < self.PWM_DEADBAND_PCT:
            return False
        if not self.set_fan_speed(value):
            return False
        self._applied_pct = value
        self._last_write_t = now
        return True

    # --- жизненный цикл ---------------------------------------------------
    def enable(self):
        if not self.is_available():
            return False
        self._mode(True)
        self.enabled = True
        self._last_temp = None
        self._applied_pct = None
        self.start_background()
        return True

    def disable(self):
        self.enabled = False
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(2)
        self._mode(False)
        self._applied_pct = None
        self._target_pct = None
        self._last_temp = None
        return True

    def start_background(self, interval: float = None):
        if not self.is_available():
            return False
        if interval is not None:
            self.interval = float(interval)
        if self._thread and self._thread.is_alive():
            return True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='FanCurve')
        self._thread.start()
        return True

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.apply()
            except Exception as e:
                self.last_error = str(e)
                logger.debug('fan loop: %s', e)
            self._stop.wait(getattr(self, 'interval', self.POLL_SEC))

    # --- кривая -----------------------------------------------------------
    def validate_curve(self, c):
        """(ok, message): >=2 точек, температуры 20..110, скважность 0..100, скважность не убывает."""
        try:
            pts = sorted((int(k), int(v)) for k, v in c.items())
        except (TypeError, ValueError, AttributeError):
            return False, 'curve must map temperatures to fan percentages'
        if len(pts) < 2:
            return False, 'curve needs at least 2 points'
        for temp, pwm in pts:
            if not (20 <= temp <= 110):
                return False, f'temperature {temp} out of range 20..110'
            if not (0 <= pwm <= 100):
                return False, f'fan speed {pwm} out of range 0..100'
        for (_, a), (_, b) in zip(pts, pts[1:]):
            if b < a:
                return False, 'fan speed must not decrease as temperature rises'
        return True, ''

    def set_curve(self, c):
        ok, msg = self.validate_curve(c)
        if not ok:
            raise FanControllerException(msg)
        self.curve = {int(k): int(v) for k, v in c.items()}
        self._last_temp = None
        return True

    def get_current_curve(self):
        return dict(self.curve)

    def reset_curve(self):
        self.curve = self.DEFAULT_CURVE.copy()
        self._last_temp = None
        return True

    def get_stats(self):
        t = self.read_temperature()
        rpm, pwm = [], []
        for p, _ in self.devices:
            try:
                pwm.append(round(int(p.read_text().strip()) * 100.0 / 255.0, 1))
            except (OSError, ValueError):
                pwm.append(None)
        for p, _ in self.devices:
            n = p.name[3:]
            rp = p.parent / ('fan' + n + '_input')
            try:
                rpm.append(int(rp.read_text().strip()))
            except (OSError, ValueError):
                rpm.append(None)
        return {'available': self.is_available(), 'enabled': self.enabled,
                'current_temperature': t,
                'calculated_fan_speed': self.calc(t) if t is not None else None,
                'target_fan_speed': self._target_pct,
                'applied_fan_speed': self._applied_pct,
                'sensors': len(self.temp_paths),
                'tdp_boost_pct': self._tdp_boost_now(time.monotonic()),
                'channels': len(self.devices), 'pwm_percent': pwm, 'fan_rpm': rpm,
                'last_error': self.last_error}
