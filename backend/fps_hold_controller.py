# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Контроллер удержания FPS (версия 2.1.1).

Цель: держать FPS не ниже эффективной цели (заданная + EFFECTIVE_OFFSET),
не уходя заметно выше неё и не поднимая TDP выше плато.

Правила:
  * Коридор (deadband): |fps - goal| <= deadband — TDP не меняем.
  * Дефицит (fps < goal - deadband): поднимаем TDP. Шаг 1..3 W зависит от дефицита.
    Подъём не чаще raise_interval_sec.
  * Избыток (fps > goal + deadband) должен быть устойчивым: держаться не меньше
    surplus_confirm_sec. Тогда снижаем TDP на 1 W не чаще lower_interval_sec.
    Один кадр выше цели понижения не вызывает.
  * Плато: после подъёма контроллер проверяет через plateau_sec, вырос ли сглаженный
    FPS на plateau_gain. Если нет, текущий TDP становится потолком на plateau_hold_sec:
    выше не поднимаем, даже при дефиците. Понижение от потолка не запрещено.
  * Лучше больше, чем меньше: при неполных данных TDP не снижаем.
"""

from collections import deque
from typing import Deque, Optional, Tuple

EFFECTIVE_OFFSET = 2


class FpsHoldController:
    def __init__(self, deadband: float = 2.0, smooth_sec: float = 4.0,
                 raise_interval_sec: float = 2.0, lower_interval_sec: float = 8.0,
                 surplus_confirm_sec: float = 10.0, min_w: float = 5.0, max_w: float = 80.0,
                 step_lower: float = 1.0, plateau_sec: float = 6.0,
                 plateau_gain: float = 1.0, plateau_hold_sec: float = 60.0):
        self.deadband = float(deadband)
        self.smooth_sec = float(smooth_sec)
        self.raise_interval_sec = float(raise_interval_sec)
        self.lower_interval_sec = float(lower_interval_sec)
        self.surplus_confirm_sec = float(surplus_confirm_sec)
        self.min_w = float(min_w)
        self.max_w = float(max_w)
        self.step_lower = float(step_lower)
        self.plateau_sec = float(plateau_sec)
        self.plateau_gain = float(plateau_gain)
        self.plateau_hold_sec = float(plateau_hold_sec)
        self._fps: Deque[Tuple[float, float]] = deque()
        self._surplus_since: Optional[float] = None
        self._last_raise = -1e9
        self._last_lower = -1e9
        self._probe: Optional[Tuple[float, float, float]] = None  # (t_raise, from_w, fps_before)
        self._ceiling: Optional[Tuple[float, float]] = None       # (ceiling_w, until)
        self.reason = ""

    # --- измерения -------------------------------------------------------
    def observe(self, now: float, fps: Optional[float]) -> None:
        if fps is None:
            return
        self._fps.append((now, float(fps)))
        while self._fps and now - self._fps[0][0] > self.smooth_sec:
            self._fps.popleft()

    def smoothed(self) -> Optional[float]:
        if not self._fps:
            return None
        return sum(f for _, f in self._fps) / len(self._fps)

    # --- потолок плато ---------------------------------------------------
    def ceiling_now(self, now: float) -> Optional[float]:
        if self._ceiling and self._ceiling[1] > now:
            return self._ceiling[0]
        return None

    def _check_plateau(self, now: float, cur_w: float) -> None:
        if self._probe is None:
            return
        t0, from_w, fps_before = self._probe
        if now - t0 < self.plateau_sec:
            return
        self._probe = None
        fps_now = self.smoothed()
        if fps_now is None:
            return
        gain = fps_now - fps_before
        if gain < self.plateau_gain:
            self._ceiling = (cur_w, now + self.plateau_hold_sec)
            self.reason = f"плато: {from_w:g}->{cur_w:g} W дали {gain:+.1f} fps, потолок {cur_w:g} W"

    # --- решение ---------------------------------------------------------
    def decide(self, now: float, cur_w: float, goal: float,
               ceiling: Optional[float] = None) -> float:
        """Новое значение TDP (может совпадать с cur_w)."""
        fps = self.smoothed()
        if fps is None:
            self.reason = "нет данных FPS"
            self._surplus_since = None
            return cur_w

        self._check_plateau(now, cur_w)
        ceil = self.ceiling_now(now)
        if ceiling is not None:
            ceil = ceiling if ceil is None else min(ceil, ceiling)

        dev = fps - goal
        if dev < -self.deadband:
            self._surplus_since = None
            if now - self._last_raise < self.raise_interval_sec:
                self.reason = f"дефицит {dev:+.1f}, ждём интервал подъёма"
                return cur_w
            if ceil is not None and cur_w >= ceil:
                self.reason = f"дефицит {dev:+.1f}, потолок плато {ceil:g} W: выше не поднимаем"
                return cur_w
            deficit = -dev
            step = 1.0 if deficit < 3 else (2.0 if deficit < 6 else 3.0)
            target = cur_w + step
            if ceil is not None and target > ceil:
                target = ceil
            new = min(self.max_w, target)
            if new > cur_w:
                self._last_raise = now
                # Проба ставится один раз на окно измерения: повторный подъём не сбрасывает её,
                # иначе при подъёмах чаще plateau_sec проверка плато никогда не сработает.
                if self._probe is None:
                    self._probe = (now, cur_w, fps)
                self.reason = f"дефицит {dev:+.1f}, подъём {cur_w:g}->{new:g} W"
            return new

        if dev > self.deadband:
            if self._surplus_since is None:
                self._surplus_since = now
            held = now - self._surplus_since
            if held < self.surplus_confirm_sec:
                self.reason = f"избыток {dev:+.1f}, подтверждение {held:.0f}/{self.surplus_confirm_sec:.0f} с"
                return cur_w
            if now - self._last_lower < self.lower_interval_sec:
                self.reason = f"избыток {dev:+.1f}, ждём интервал снижения"
                return cur_w
            new = max(self.min_w, cur_w - self.step_lower)
            if new < cur_w:
                self._last_lower = now
                self.reason = f"устойчивый избыток {dev:+.1f}, снижение {cur_w:g}->{new:g} W"
            return new

        self._surplus_since = None
        self.reason = f"в коридоре ({dev:+.1f} fps)"
        return cur_w
