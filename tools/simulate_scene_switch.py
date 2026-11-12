#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Симуляция «локация -> меню -> локация» на настоящем FpsHoldController.

Модель игры: FPS = need_fps * (W / need_w) ** 0.9, не выше кэпа сцены, плюс шум.
  * локация: 42 fps на 35 W (цель 40 + 2), кэп 60;
  * меню: 60 fps уже на 9 W, кэп 60.
Опрос раз в interval секунд, FPS — среднее за последние 0.6 с (как AVG_SAMPLES=30
при ~48 строках/с в логе mangoapp). TDP применяется мгновенно.

Печатает для каждого возврата из меню:
  * сколько секунд FPS был ниже goal-4 (жёсткая просадка);
  * через сколько секунд FPS снова >= goal-2;
  * максимум TDP в первые 15 с после возврата (перелёт).

Запуск из папки проекта:
    python3 tools/simulate_scene_switch.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.fps_hold_controller import FpsHoldController  # noqa: E402

GOAL = 42.0
SCENES = {
    'location': dict(need_fps=42.0, need_w=35.0, cap=60.0),
    'menu': dict(need_fps=60.0, need_w=9.0, cap=60.0),
    'heavy': dict(need_fps=42.0, need_w=48.0, cap=60.0),
}


def fps_of(scene, w, rng, noise):
    s = SCENES[scene]
    f = s['need_fps'] * (max(w, 1.0) / s['need_w']) ** 0.9
    return max(1.0, min(s['cap'], f) + rng.uniform(-noise, noise))


def run(timeline, seed=1, noise=1.5, interval=1.0, start_w=35.0, ctl_factory=None, game='sim'):
    """timeline: [(scene, seconds)]. Возвращает список отчётов по входам в 'location'."""
    rng = random.Random(seed)
    ctl = ctl_factory() if ctl_factory else FpsHoldController(min_w=5, max_w=80)
    ctl.raise_interval_sec = max(0.5, interval)
    ctl.plateau_sec = max(3.0, interval * 3.0)
    if hasattr(ctl, 'set_game'):
        ctl.set_game(game)
    dt = 0.1
    t = 0.0
    w = start_w
    frames = []          # (t, fps) с шагом dt
    next_poll = 0.0
    trace = []           # (t, scene, fps, w)
    for scene, dur in timeline:
        end = t + dur
        while t < end - 1e-9:
            f = fps_of(scene, w, rng, noise)
            frames.append((t, f))
            if t >= next_poll - 1e-9:
                recent = [x for tt, x in frames if t - tt <= 0.6]
                reading = sum(recent) / len(recent)
                ctl.observe(t, reading)
                new = ctl.decide(t, w, GOAL)
                w = max(5.0, min(80.0, new))
                next_poll = t + interval
            trace.append((t, scene, f, w))
            t += dt
    return trace


def report(trace, scene='location'):
    out = []
    prev = None
    for i, (t, sc, f, w) in enumerate(trace):
        if sc == scene and prev is not None and prev != scene:
            seg = [x for x in trace[i:] if x[0] - t <= 30 and x[1] == scene]
            hard = sum(0.1 for x in seg if x[2] < GOAL - 4)
            ok_t = next((x[0] - t for x in seg if x[2] >= GOAL - 2 and
                         all(y[2] >= GOAL - 4 for y in seg if x[0] <= y[0] <= x[0] + 1)), None)
            peak = max(x[3] for x in seg if x[0] - t <= 15)
            w_in = w
            w30 = seg[-1][3]
            out.append(dict(t=round(t), from_scene=prev, w_in=round(w_in, 1), hard_s=round(hard, 1),
                            recover_s=None if ok_t is None else round(ok_t, 1),
                            peak_w=round(peak, 1), w_after_30s=round(w30, 1)))
        prev = sc
    return out


SCENARIO = [('location', 120), ('menu', 40), ('location', 60), ('menu', 25),
            ('location', 60), ('menu', 90), ('location', 60), ('heavy', 40), ('menu', 30), ('location', 60)]


def main():
    for seed in (1, 2, 3):
        print(f'seed {seed}')
        for r in report(run(SCENARIO, seed=seed)):
            print('  ', r)


if __name__ == '__main__':
    main()
