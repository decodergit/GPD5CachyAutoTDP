# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Модель соотношения FPS и TDP (версия 2.1.0).

Правило: TDP не поднимается, если повышение не дало роста FPS.

Оценка выполняется по факту, а не по наличию данных для нового уровня:
  * note_raise(now, from_tdp) вызывается монитором при каждом успешном подъёме TDP.
    Модель запоминает средний FPS за окно до подъёма (fps_before).
  * Пока не прошло settle_sec, новые подъёмы блокируются (эффект ещё не измерен).
  * После settle_sec модель считает средний FPS с момента подъёма (fps_after).
    Если fps_after - fps_before < min_gain, включается потолок: TDP не поднимается
    выше уровня, с которого был подъём, на hold_sec.
  * Потолок снимается по истечении hold_sec, поэтому модель может пересмотреть решение.
Понижение TDP модель не ограничивает.

Таблица уровень TDP -> средний FPS за окно ведётся для диагностики и для случая,
когда есть измерения и на текущем, и на следующем уровне (сравнение напрямую).
"""

from collections import deque
from typing import Deque, Dict, Optional, Tuple


class FpsTdpModel:
    def __init__(self, window_sec: float = 15.0, min_gain: float = 1.0,
                 hold_sec: float = 30.0, settle_sec: float = 5.0, bin_w: float = 1.0):
        self.window_sec = float(window_sec)
        self.min_gain = float(min_gain)
        self.hold_sec = float(hold_sec)
        self.settle_sec = float(settle_sec)
        self.bin_w = float(bin_w)
        self._samples: Deque[Tuple[float, float, float]] = deque()  # (t, tdp, fps)
        self._pending: Optional[Tuple[float, float, Optional[float]]] = None  # (t_raise, from_tdp, fps_before)
        self._cap: Optional[Tuple[float, float]] = None  # (cap_tdp, until)
        self.last_reason: str = ""

    def _level(self, tdp: float) -> float:
        return round(round(tdp / self.bin_w) * self.bin_w, 3)

    def record(self, now: float, tdp: float, fps: Optional[float]) -> None:
        if fps is None or tdp is None:
            return
        self._samples.append((float(now), float(tdp), float(fps)))
        self._trim(now)

    def _trim(self, now: float) -> None:
        while self._samples and now - self._samples[0][0] > self.window_sec:
            self._samples.popleft()

    def _mean_fps(self, since: Optional[float] = None, until: Optional[float] = None) -> Optional[float]:
        vals = [f for t, _, f in self._samples
                if (since is None or t >= since) and (until is None or t <= until)]
        return sum(vals) / len(vals) if vals else None

    def table(self, now: float) -> Dict[float, Dict[str, float]]:
        """Уровень TDP -> {'fps': средний FPS, 'n': число измерений} за окно."""
        self._trim(now)
        acc: Dict[float, list] = {}
        for _, tdp, fps in self._samples:
            acc.setdefault(self._level(tdp), []).append(fps)
        return {lvl: {"fps": sum(v) / len(v), "n": len(v)} for lvl, v in sorted(acc.items())}

    def note_raise(self, now: float, from_tdp: float) -> None:
        """Монитор сообщает, что TDP только что подняли с from_tdp."""
        self._trim(now)
        self._pending = (float(now), float(from_tdp), self._mean_fps(since=now - self.window_sec, until=now))

    def allow_raise(self, now: float, cur: float, step: float) -> bool:
        """Можно ли поднять TDP с cur на step."""
        target = self._level(cur + step)
        self._trim(now)

        if self._cap and self._cap[1] > now and target > self._cap[0]:
            self.last_reason = f"cap {self._cap[0]:g}W: no FPS gain after raise"
            return False

        if self._pending is not None:
            t_raise, from_tdp, fps_before = self._pending
            if now - t_raise < self.settle_sec:
                self.last_reason = f"settling after raise {from_tdp:g}W->{cur:g}W"
                return False
            fps_after = self._mean_fps(since=t_raise + self.settle_sec, until=now)
            self._pending = None
            if fps_before is not None and fps_after is not None:
                gain = fps_after - fps_before
                if gain < self.min_gain:
                    self._cap = (self._level(cur), now + self.hold_sec)
                    self.last_reason = (f"no FPS gain {from_tdp:g}W->{cur:g}W "
                                        f"({gain:+.1f} fps): cap {self._level(cur):g}W")
                    return False
                self.last_reason = f"FPS gain {gain:+.1f} after {from_tdp:g}W->{cur:g}W"
            else:
                self.last_reason = "no FPS data after raise: raise allowed"

        tbl = self.table(now)
        base = self._level(cur)
        if target in tbl and base in tbl:
            gain = tbl[target]["fps"] - tbl[base]["fps"]
            if gain < self.min_gain:
                self._cap = (base, now + self.hold_sec)
                self.last_reason = f"table: no FPS gain {base:g}W->{target:g}W ({gain:+.1f} fps)"
                return False
        if not self.last_reason.startswith("no FPS") and not self.last_reason.startswith("FPS gain"):
            self.last_reason = f"raise {base:g}W->{target:g}W allowed"
        return True

    def hold_level(self, now: float) -> Optional[float]:
        """Потолок TDP, действующий сейчас (или None)."""
        if self._cap and self._cap[1] > now:
            return self._cap[0]
        return None
