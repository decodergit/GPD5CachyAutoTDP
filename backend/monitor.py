# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Цикл автоматического управления TDP (версия 2.4.0).

Решение принимает FpsHoldController. CPU load boost — отдельная ветка с собственным шагом
и тем же потолком плато, что и FPS-удержание.
Границы min/max всегда берутся из параметров пользователя (через _sync_bounds).
"""

import logging
import threading
import time
from typing import Any

from .tdp_controller import TDPController
from .fps_reader import FPSReader
from .fps_hold_controller import FpsHoldController

logger = logging.getLogger(__name__)


class TDPMonitorException(Exception):
    pass


# Эффективная цель FPS = заданная пользователем + EFFECTIVE_OFFSET.
EFFECTIVE_OFFSET = 2
LOAD_BOOST_STEP_W = 5.0
LOAD_BOOST_INTERVAL_SEC = 1.5


class TDPMonitor:
    STATE_STOPPED = 'stopped'
    STATE_RUNNING = 'running'
    STATE_WAITING = 'waiting'
    STATE_ERROR = 'error'

    def __init__(self, tdp: TDPController, config_manager: Any, fan=None):
        self.tdp = tdp
        self.cfg = config_manager
        self.fan = fan
        self.fps = FPSReader()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._running = False
        self.state = self.STATE_STOPPED
        self._waiting_since = None
        self.target_fps = 40
        self.min_tdp = float(tdp.min_w)
        self.max_tdp = float(tdp.max_w)
        self.last_fps = None
        self.last_cpu_load = None
        self.last_gpu_load = None
        self.last_tdp = None
        self.fps_ctl = FpsHoldController(min_w=self.min_tdp, max_w=self.max_tdp)
        self.tdp_hold_level = None
        self.tdp_decision = ''
        self._stats = {'adjustments_made': 0, 'errors': 0, 'last_error': None,
                       'total_runtime_sec': 0, 'load_boosts_made': 0}

    # ------------------------------------------------------------------
    # Управление жизненным циклом
    # ------------------------------------------------------------------
    def start(self, min_tdp=15., max_tdp=80., target_fps=40, initial_tdp=None):
        if not self.tdp.available():
            raise TDPMonitorException('No real TDP backend available')
        if min_tdp > max_tdp or target_fps < 1:
            raise TDPMonitorException('Invalid monitor parameters')
        with self._lock:
            if self._running:
                return False
            self.min_tdp = max(self.tdp.min_w, float(min_tdp))
            self.max_tdp = min(self.tdp.max_w, float(max_tdp))
            self.target_fps = int(target_fps)
            self._sync_bounds()
            self.fps_ctl.reset()
            cur = self.tdp.current_w
            if cur is None:
                saved_tdp = self.cfg.get_value('last_tdp', None)
                if saved_tdp is not None:
                    cur = saved_tdp
                else:
                    cur = initial_tdp if initial_tdp is not None else self.cfg.get_value('initial_tdp', 35)
            cur = max(self.min_tdp, min(self.max_tdp, float(cur)))
            try:
                self.tdp.set_tdp(cur)
            except Exception as e:
                self.state = self.STATE_ERROR
                self._stats['last_error'] = str(e)
                self._stats['errors'] += 1
                raise
            self.last_tdp = cur
            self.cfg.set_internal('last_tdp', cur)
            self._running = True
            self.state = self.STATE_WAITING
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='AutoTDP')
        self._thread.start()
        return True

    def stop(self, reset_to_initial=True):
        with self._lock:
            self._running = False
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(3)
        reset_error = None
        if reset_to_initial:
            try:
                initial = float(self.cfg.get_value('initial_tdp', 35))
                initial = max(self.tdp.min_w, min(self.tdp.max_w, initial))
                self.tdp.set_tdp(initial)
                self.last_tdp = initial
                self.cfg.set_internal('last_tdp', initial)
            except Exception as e:
                reset_error = str(e)
                logger.error('Failed to restore initial TDP: %s', e, exc_info=True)
        with self._lock:
            self.state = self.STATE_STOPPED
            self._waiting_since = None
            # Потолок плато и окна не должны переходить в следующий запуск.
            self.fps_ctl.reset()
            self.tdp_hold_level = None
            self.tdp_decision = ''
        if reset_error:
            raise TDPMonitorException(reset_error)
        return True

    def set_parameters(self, min_tdp=None, max_tdp=None, target_fps=None):
        with self._lock:
            if min_tdp is not None:
                self.min_tdp = float(min_tdp)
            if max_tdp is not None:
                self.max_tdp = float(max_tdp)
            if self.min_tdp > self.max_tdp:
                self.min_tdp, self.max_tdp = self.max_tdp, self.min_tdp
            if target_fps is not None:
                self.target_fps = int(target_fps)
            self._sync_bounds()
        return True

    def _sync_bounds(self):
        # Контроллер работает в границах пользователя, а не в границах железа.
        self.fps_ctl.min_w = float(self.min_tdp)
        self.fps_ctl.max_w = float(self.max_tdp)
        # Интервал подъёма и окно плато привязываем к периоду опроса: если опрашивать
        # чаще, чем разрешён подъём, шаг всё равно ждёт опроса. Плато проверяем на
        # нескольких замерах, иначе при частом опросе решение принимается по шуму.
        try:
            interval = float(self.cfg.get_value('check_interval_sec', 1))
        except (TypeError, ValueError):
            interval = 1.0
        interval = max(0.5, min(10.0, interval))
        self.fps_ctl.raise_interval_sec = max(0.5, interval)
        self.fps_ctl.plateau_sec = max(3.0, interval * 3.0)

    # ------------------------------------------------------------------
    # Установка TDP
    # ------------------------------------------------------------------
    def _apply(self, new: float, load_boost: bool = False) -> bool:
        """Единственная точка записи TDP в цикле. Возвращает True, если значение реально изменилось."""
        cur = self.last_tdp if self.last_tdp is not None else new
        new = max(self.min_tdp, min(self.max_tdp, float(new)))
        if abs(new - cur) < 0.5:
            return False
        self.tdp.set_tdp(new)
        # Опережение вентилятора: температура растёт с задержкой, раскручиваем заранее.
        if self.fan is not None and hasattr(self.fan, 'note_tdp_change'):
            try:
                self.fan.note_tdp_change(cur, new)
            except Exception as e:
                logger.debug('fan feed-forward failed: %s', e)
        self.last_tdp = new
        self._stats['adjustments_made'] += 1
        if load_boost:
            self._stats['load_boosts_made'] += 1
        return True

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    def _loop(self):
        started = time.time()
        last_boost = 0.0
        while not self._stop.is_set():
            try:
                metrics = self.fps.read_metrics()
                fps = metrics.get('fps')
                cpu = metrics.get('cpu_load')
                gpu = metrics.get('gpu_load')
                self.last_fps = fps
                self.last_cpu_load = cpu
                self.last_gpu_load = gpu
                cur_read = self.tdp.read_tdp()
                if cur_read is not None:
                    self.last_tdp = cur_read
                if fps is None or self.last_tdp is None:
                    if self.state != self.STATE_WAITING or self._waiting_since is None:
                        self._waiting_since = time.monotonic()
                    self.state = self.STATE_WAITING
                else:
                    self._waiting_since = None
                    cur = float(self.last_tdp)
                    now = time.time()
                    threshold = float(self.cfg.get_value('load_boost_threshold', 95))
                    boost_enabled = bool(self.cfg.get_value('load_boost_enabled', True))
                    effective = float(self.target_fps) + EFFECTIVE_OFFSET
                    high_cpu = cpu is not None and cpu > threshold
                    high_gpu = gpu is not None and gpu > threshold
                    # CPU load boost не зависит от FPS (компиляция шейдеров).
                    # GPU load boost — только при дефиците FPS, иначе жёсткий кап FPS поднимет TDP до максимума.
                    load_boost = boost_enabled and (high_cpu or (high_gpu and fps < effective))

                    if load_boost:
                        # Потолок плато действует и на буст: не выше, чем контроллер уже признал бесполезным.
                        ceil = self.fps_ctl.ceiling_now(now)
                        target = cur + LOAD_BOOST_STEP_W
                        if ceil is not None:
                            target = min(target, ceil)
                        if now - last_boost >= LOAD_BOOST_INTERVAL_SEC and target > cur + 0.5:
                            if self._apply(target, load_boost=True):
                                last_boost = now
                        self.tdp_hold_level = ceil
                        self.tdp_decision = 'load boost' if target > cur + 0.5 else 'load boost: потолок плато'
                    else:
                        self.fps_ctl.observe(now, fps)
                        new_w = self.fps_ctl.decide(now, cur, effective)
                        self.tdp_decision = self.fps_ctl.reason
                        if abs(new_w - cur) >= 0.5:
                            if not self._apply(new_w):
                                # Изменение обрезано границей — проба плато не должна считать его состоявшимся.
                                self.fps_ctl.cancel_probe()
                        self.tdp_hold_level = self.fps_ctl.ceiling_now(now)
                    self.state = self.STATE_RUNNING
                self._stats['total_runtime_sec'] = int(time.time() - started)
            except Exception as e:
                logger.error('monitor: %s', e, exc_info=True)
                self._stats['errors'] += 1
                self._stats['last_error'] = str(e)
                self.state = self.STATE_ERROR
            self._stop.wait(float(self.cfg.get_value('check_interval_sec', 1)))

    def get_stats(self):
        with self._lock:
            return {
                'state': self.state,
                'running': self._running,
                'target_fps': self.target_fps,
                'min_tdp': self.min_tdp,
                'max_tdp': self.max_tdp,
                'last_fps': self.last_fps,
                'last_cpu_load': self.last_cpu_load,
                'last_gpu_load': self.last_gpu_load,
                'load_boost_enabled': bool(self.cfg.get_value('load_boost_enabled', True)),
                'load_boost_threshold': float(self.cfg.get_value('load_boost_threshold', 95)),
                'last_tdp': self.last_tdp,
                'effective_target_fps': self.target_fps + EFFECTIVE_OFFSET,
                'tdp_hold_level': self.tdp_hold_level,
                'tdp_decision': self.tdp_decision,
                'tdp_search': self.fps_ctl.search_state(),
                'tdp_search': self.fps_ctl.search_state(),
                **self._stats,
                'fps_source': self.fps.path and str(self.fps.path),
                'waiting_seconds': (max(0.0, time.monotonic() - self._waiting_since)
                                    if self.state == self.STATE_WAITING and self._waiting_since is not None else 0.0),
            }
