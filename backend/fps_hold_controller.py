# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Контроллер удержания FPS (версия 2.4.0).

Цель: держать FPS не ниже эффективной цели (заданная + EFFECTIVE_OFFSET) при наименьшем TDP.

Подъём (дефицит кадров) — пошаговый, как раньше:
  * fps < goal - deadband: TDP += шаг, пропорциональный диапазону TDP и дефициту кадров,
    не чаще raise_interval_sec;
  * плато: если подъём не дал +plateau_gain fps за plateau_sec, текущий TDP — потолок
    на plateau_hold_sec.

Снижение (избыток кадров) — поиск минимума делением отрезка:
  * good_w — наименьший TDP, на котором цель держалась;
  * bad_w — наибольший TDP, на котором кадров не хватало (если неизвестен — min_w);
  * проба = середина (good_w + bad_w) / 2, но не ниже good_w - max_probe_step_w;
  * оценка пробы: среднее FPS по замерам, сделанным позже settle_sec после установки,
    за время не меньше probe_sec. Успех (fps >= goal - success_tolerance) -> good_w = проба.
    Провал -> bad_w = проба и немедленный возврат к good_w;
  * сильный провал (fps < goal - fail_fast_fps) завершает пробу досрочно;
  * поиск окончен, когда good_w - bad_w <= resolution_w: TDP стоит на good_w;
  * границы сбрасываются: при дефиците на good_w (сцена стала тяжелее), при любом подъёме
    и по истечении bounds_ttl_sec.

Лучше больше, чем меньше: при неполных данных TDP не снижается.
"""

from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

EFFECTIVE_OFFSET = 2


class FpsHoldController:
    # Шаг подъёма выше выученного потолка: только маленькая проба.
    REPROBE_STEP_W = 2.0
    # Выше выученного потолка поднимаемся редко: сцена могла стать тяжелее, но
    # частые пробы только жгли бы мощность.
    REPROBE_INTERVAL_SEC = 10.0

    def __init__(self, deadband: float = 2.0, smooth_sec: float = 4.0,
                 raise_interval_sec: float = 2.0, surplus_confirm_sec: float = 3.0,
                 min_w: float = 5.0, max_w: float = 80.0,
                 raise_gain: float = 0.35, raise_max_frac: float = 0.5,
                 raise_probe_frac: float = 0.12, min_gain_per_w: float = 0.15,
                 plateau_sec: float = 6.0, plateau_gain: float = 1.0,
                 plateau_hold_sec: float = 60.0,
                 settle_sec: float = 1.0, probe_sec: float = 4.0,
                 max_probe_step_w: float = 16.0, resolution_w: float = 2.0,
                 success_tolerance: float = 0.0, fail_fast_fps: float = 4.0,
                 bounds_ttl_sec: float = 90.0, research_after_sec: float = 20.0):
        self.deadband = float(deadband)
        self.smooth_sec = float(smooth_sec)
        self.raise_interval_sec = float(raise_interval_sec)
        self.surplus_confirm_sec = float(surplus_confirm_sec)
        self._goal_now = 60.0
        self.min_w = float(min_w)
        self.max_w = float(max_w)
        self.raise_gain = float(raise_gain)
        self.raise_max_frac = float(raise_max_frac)
        self.raise_probe_frac = float(raise_probe_frac)
        self.min_gain_per_w = float(min_gain_per_w)
        self.plateau_sec = float(plateau_sec)
        self.plateau_gain = float(plateau_gain)
        self.plateau_hold_sec = float(plateau_hold_sec)
        self.settle_sec = float(settle_sec)
        self.probe_sec = float(probe_sec)
        self.max_probe_step_w = float(max_probe_step_w)
        self.resolution_w = float(resolution_w)
        self.success_tolerance = float(success_tolerance)
        self.fail_fast_fps = float(fail_fast_fps)
        self.bounds_ttl_sec = float(bounds_ttl_sec)
        self.research_after_sec = float(research_after_sec)
        self._fps: Deque[Tuple[float, float]] = deque(maxlen=256)
        self.last_search_probes = 0
        self.reset()

    # --- состояние ------------------------------------------------------
    def reset(self) -> None:
        """Полный сброс: окна, потолок плато, проба плато, границы поиска."""
        self._fps.clear()
        self._surplus_since: Optional[float] = None
        self._last_raise = -1e9
        self._probe: Optional[Tuple[float, float, float]] = None   # плато: (t, from_w, fps_before)
        self._ceiling: Optional[Tuple[float, float]] = None        # (ceiling_w, until)
        self._learned_ceiling: Optional[float] = None              # потолок без срока действия
        self._fail_streak = 0                                     # провалов пробы плато подряд
        self._reset_search()
        self.reason = ""

    def _reset_search(self) -> None:
        if getattr(self, '_probes', 0):
            self.last_search_probes = self._probes
        self._good_w: Optional[float] = None
        self._bad_w: Optional[float] = None
        self._bounds_t = -1e9
        self._search_probe: Optional[Tuple[float, float]] = None   # (t_set, probe_w)
        self._done = False
        self._done_t = -1e9
        self._probes = 0
        self._resume_t = -1e9   # момент возврата на good_w после провала пробы

    def cancel_probe(self) -> None:
        """Изменение TDP не состоялось (обрезано границей): отменяем обе пробы."""
        self._probe = None
        self._search_probe = None

    def search_state(self) -> Dict[str, Any]:
        if self._search_probe is not None:
            state = 'probing'
        elif self._done:
            state = 'done'
        elif self._good_w is not None:
            state = 'searching'
        else:
            state = 'idle'
        return {'state': state, 'good_w': self._good_w, 'bad_w': self._bad_w,
                'probe_w': self._search_probe[1] if self._search_probe else None,
                'probes': self._probes, 'last_search_probes': max(self._probes, self.last_search_probes)}

    # --- измерения -------------------------------------------------------
    def observe(self, now: float, fps: Optional[float]) -> None:
        if fps is None:
            return
        self._fps.append((now, float(fps)))

    def _mean(self, since: float, until: float) -> Tuple[Optional[float], int]:
        vals = [f for t, f in list(self._fps) if since <= t <= until]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

    def smoothed(self, now: Optional[float] = None) -> Optional[float]:
        snapshot = list(self._fps)  # копия: окно может меняться из другого потока
        if not snapshot:
            return None
        end = snapshot[-1][0] if now is None else now
        vals = [f for t, f in snapshot if end - t <= self.smooth_sec]
        if not vals:
            vals = [snapshot[-1][1]]
        return sum(vals) / len(vals)

    # --- потолок плато ---------------------------------------------------
    def ceiling_now(self, now: float) -> Optional[float]:
        if self._ceiling and self._ceiling[1] > now:
            return self._ceiling[0]
        return None

    def _check_plateau(self, now: float, cur_w: float) -> None:
        """Проверяет, дал ли подъём TDP соразмерный прирост FPS.

        Требуемый прирост зависит от размера подъёма: шаг на 12 Вт должен дать больше
        кадров, чем шаг на 2 Вт, иначе «плато» не отличить от нормального отклика.
        Поэтому порог = plateau_gain + min_gain_per_w * (поднято ватт).

        Сравнивается устойчивое среднее до подъёма с устойчивым средним в конце окна.
        Окно должно быть длиннее интервала опроса: при опросе 3 с и окне 3 с между
        подъёмом и проверкой проходит один замер, и решение принимается по шуму.
        """
        if self._probe is None:
            return
        t0, from_w, fps_before = self._probe
        if now - t0 < self.plateau_sec:
            return
        fps_after, n_after = self._mean(t0 + self.settle_sec, now)
        if fps_after is None or n_after < 2:
            # Мало замеров после подъёма — ждём ещё.
            if now - t0 < self.plateau_sec * 3:
                return
        self._probe = None
        if fps_after is None or fps_before is None:
            return
        raised = max(1.0, cur_w - from_w)
        required = self.plateau_gain + self.min_gain_per_w * raised
        gain = fps_after - fps_before
        # Потолок имеет смысл только если кадров всё ещё не хватает. Если подъём вывел
        # FPS на цель, «маленький прирост» — не плато, а уже достигнутый результат.
        still_short = fps_after < self._goal_now - self.deadband
        if gain < required and still_short:
            # Один провал может быть шумом: за окно проходит два-три замера, и ±1.5 fps
            # шума легко перекрывают порог. Потолок ставим только после двух провалов
            # подряд, иначе на ровном месте теряются ватты, которые ещё давали кадры.
            self._fail_streak += 1
            if self._fail_streak >= 2:
                self._ceiling = (cur_w, now + self.plateau_hold_sec)
                self._learned_ceiling = cur_w
                self._fail_streak = 0
        else:
            self._fail_streak = 0
            self.reason = (f"плато: {from_w:g}->{cur_w:g} W дали {gain:+.1f} fps "
                           f"(нужно {required:.1f}), потолок {cur_w:g} W")

    def _raise_step(self, deficit: float, goal: float, cur_w_for_step: float = 0.0) -> float:
        """Шаг подъёма TDP при дефиците кадров.

        Шаг пропорционален двум величинам:
          * ширине доступного диапазона TDP (max_w - min_w) — на широком диапазоне
            один шаг должен быть больше, иначе набор занимает десятки секунд;
          * относительному дефициту (deficit / goal) — чем сильнее не хватает кадров,
            тем крупнее шаг.
        Сверху шаг ограничен долей диапазона raise_max_frac, чтобы не перескакивать
        через рабочий уровень. Снизу — 1 Вт. Пока идёт проверка плато, шаг уменьшается:
        иначе за одно окно можно уйти далеко вверх и не заметить, что прирост кончился.
        """
        span = max(1.0, float(self.max_w) - float(self.min_w))
        rel = max(0.0, min(1.0, deficit / goal)) if goal > 0 else 0.0
        step = span * self.raise_gain * rel
        cap = span * self.raise_max_frac
        if self._learned_ceiling is not None:
            # Плато уже найдено однажды. Срок потолка истекает, чтобы не застрять навсегда,
            # но возвращаться к крупным шагам нельзя: выше выученного уровня это трата
            # мощности без прироста кадров, поэтому только маленькая проба.
            cap = min(cap, self.REPROBE_STEP_W)
        if self._probe is not None:
            # Пока окно проверки открыто, суммарный подъём ограничен raise_probe_frac
            # диапазона: иначе за одно окно можно уйти далеко вверх и не заметить плато.
            # Считаем от базы пробы, а не от текущего TDP: cur_w уже включает прошлые шаги
            # этого же окна, и разница обнуляла лимит.
            used = max(0.0, float(cur_w_for_step) - float(self._probe[1]))
            left = max(0.0, span * self.raise_probe_frac - used)
            cap = min(cap, left)
        return max(1.0, min(cap, step))

    # --- поиск минимума делением отрезка ---------------------------------
    def _lower_bound(self) -> float:
        return self._bad_w if self._bad_w is not None else self.min_w

    def _next_probe(self) -> Optional[float]:
        """Следующая проба или None, если отрезок уже сжат до resolution_w."""
        good = self._good_w
        low = self._lower_bound()
        if good is None or good - low <= self.resolution_w:
            return None
        probe = max((good + low) / 2.0, good - self.max_probe_step_w)
        probe = float(round(probe))
        probe = max(self.min_w, min(probe, good - 1.0))
        if probe >= good or probe < self.min_w:
            return None
        return probe

    def _evaluate_search_probe(self, now: float, goal: float, cur_w: float) -> Optional[float]:
        """Возвращает новое значение TDP, если проба завершилась, иначе None (ждём)."""
        t_set, probe_w = self._search_probe
        fps_after, n = self._mean(t_set + self.settle_sec, now)
        elapsed = now - t_set
        if fps_after is None:
            if elapsed > self.probe_sec * 3:  # данных нет слишком долго — возвращаемся на безопасный уровень
                self._search_probe = None
                self.reason = f"проба {probe_w:g} W: нет данных FPS, возврат к {self._good_w:g} W"
                return self._good_w
            self.reason = f"проба {probe_w:g} W: ждём замеры"
            return None
        fail_fast = fps_after < goal - self.fail_fast_fps
        if elapsed < self.probe_sec and not fail_fast:
            self.reason = f"проба {probe_w:g} W: {fps_after:.1f} fps, измерение {elapsed:.0f}/{self.probe_sec:.0f} с"
            return None
        self._search_probe = None
        self._probes += 1
        self._bounds_t = now
        if fps_after >= goal - self.success_tolerance:
            self._good_w = probe_w
            nxt = self._next_probe()
            if nxt is None:
                self._done = True
                self._done_t = now
                self.reason = f"минимум найден: {probe_w:g} W ({fps_after:.1f} fps), проб {self._probes}"
                return None
            self._search_probe = (now, nxt)
            self.reason = f"проба {probe_w:g} W успешна ({fps_after:.1f} fps), следующая {nxt:g} W"
            return nxt
        self._bad_w = probe_w
        back = self._good_w
        self._resume_t = now
        if self._next_probe() is None:
            self._done = True
            self._done_t = now
            self.reason = f"минимум найден: {back:g} W (на {probe_w:g} W {fps_after:.1f} fps), проб {self._probes}"
        else:
            self.reason = f"проба {probe_w:g} W провалена ({fps_after:.1f} fps), возврат к {back:g} W"
        return back

    # --- решение ---------------------------------------------------------
    def decide(self, now: float, cur_w: float, goal: float,
               ceiling: Optional[float] = None) -> float:
        """Новое значение TDP (может совпадать с cur_w)."""
        self._goal_now = float(goal)
        fps = self.smoothed(now)
        if fps is None:
            self.reason = "нет данных FPS"
            self._surplus_since = None
            return cur_w

        # Границы поиска не живут вечно: условия в игре меняются.
        if self._good_w is not None and self._search_probe is None and now - self._bounds_t > self.bounds_ttl_sec:
            self._reset_search()

        # 1. Активная проба поиска: только её оценка, остальные правила ждут.
        if self._search_probe is not None:
            new = self._evaluate_search_probe(now, goal, cur_w)
            return cur_w if new is None else max(self.min_w, min(self.max_w, new))

        self._check_plateau(now, cur_w)
        ceil = self.ceiling_now(now)
        if ceiling is not None:
            ceil = ceiling if ceil is None else min(ceil, ceiling)

        dev = fps - goal

        # 1b. Продолжение поиска после провала: вернулись на good_w, отрезок ещё не сжат.
        #     Избыток для этого не нужен — достаточно, что на good_w цель держится.
        if (self._good_w is not None and not self._done and abs(cur_w - self._good_w) < 0.5
                and self._resume_t > -1e9 and dev >= -self.success_tolerance):
            fps_back, n = self._mean(self._resume_t + self.settle_sec, now)
            if fps_back is not None and now - self._resume_t >= self.settle_sec + self.probe_sec / 2:
                nxt = self._next_probe()
                self._resume_t = -1e9
                if nxt is None:
                    self._done = True
                    self._done_t = now
                    self.reason = f"минимум найден: {self._good_w:g} W, проб {self._probes}"
                    return cur_w
                self._search_probe = (now, nxt)
                self.reason = f"поиск продолжается: проба {nxt:g} W (отрезок {self._lower_bound():g}..{self._good_w:g})"
                return nxt

        # 2. Дефицит: пошаговый подъём; известные границы поиска больше не верны.
        if dev < -self.deadband:
            self._surplus_since = None
            if self._good_w is not None or self._done:
                self._reset_search()
                self._bad_w = cur_w  # здесь кадров не хватает
                self._bounds_t = now
            above_learned = self._learned_ceiling is not None and cur_w >= self._learned_ceiling - 0.5
            interval = self.REPROBE_INTERVAL_SEC if above_learned else self.raise_interval_sec
            if now - self._last_raise < interval:
                self.reason = f"дефицит {dev:+.1f}, ждём интервал подъёма"
                return cur_w
            if ceil is not None and cur_w >= ceil:
                self.reason = f"дефицит {dev:+.1f}, потолок плато {ceil:g} W: выше не поднимаем"
                return cur_w
            deficit = -dev
            step = self._raise_step(deficit, goal, cur_w)
            target = cur_w + step
            if ceil is not None and target > ceil:
                target = ceil
            new = min(self.max_w, target)
            if new > cur_w:
                self._last_raise = now
                # Первый шаг серии: запоминаем базу. Дальнейшие шаги внутри окна
                # проверки не сбрасывают пробу, но и не позволяют набрать больше
                # raise_probe_frac за шаг.
                self._probe_cur_w = new
                if self._probe is None:
                    # Среднее ДО подъёма относится к прежнему TDP — это честная база для
                    # сравнения. Значение берём за окно smooth_sec, чтобы шум не решал.
                    self._probe = (now, cur_w, fps)
                self.reason = f"дефицит {dev:+.1f}, подъём {cur_w:g}->{new:g} W"
            return new

        # 3. Избыток: поиск минимума делением отрезка.
        if dev > self.deadband:
            if self._surplus_since is None:
                self._surplus_since = now
            held = now - self._surplus_since
            if held < self.surplus_confirm_sec:
                self.reason = f"избыток {dev:+.1f}, подтверждение {held:.0f}/{self.surplus_confirm_sec:.0f} с"
                return cur_w
            if self._done:
                if now - self._done_t < self.research_after_sec:
                    self.reason = f"минимум {self._good_w:g} W найден, избыток {dev:+.1f}: ждём перед новым поиском"
                    return cur_w
                # Устойчивый избыток после завершения: сцена стала легче, ищем заново от текущего уровня.
                self._reset_search()
            if self._good_w is None or abs(self._good_w - cur_w) >= 0.5:
                # Текущий уровень держит цель с запасом — это новая верхняя граница.
                self._good_w = cur_w
                self._bounds_t = now
                if self._bad_w is not None and self._bad_w >= cur_w:
                    self._bad_w = None
            nxt = self._next_probe()
            if nxt is None:
                self._done = True
                self._done_t = now
                self.reason = f"избыток {dev:+.1f}, ниже {cur_w:g} W опускаться некуда"
                return cur_w
            self._search_probe = (now, nxt)
            self.reason = f"избыток {dev:+.1f}, проба {cur_w:g}->{nxt:g} W (отрезок {self._lower_bound():g}..{self._good_w:g})"
            return nxt

        self._surplus_since = None
        self.reason = f"в коридоре ({dev:+.1f} fps)"
        return cur_w
