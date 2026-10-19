#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Разбор CSV из collect_metrics.py (этап 4 плана).

Считает то, что нужно проверить на устройстве:
  * время падения TDP после снятия нагрузки (FPS устойчиво выше цели);
  * число снижений TDP за прогон и их размер;
  * провалы FPS вскоре после снижения TDP (цена проб вниз);
  * как часто TDP менялся (частота регулирования);
  * поведение вентилятора: сколько раз менялись обороты и ШИМ.

Запуск:
    python3 tools/analyze_metrics.py autotdp_metrics.csv --target-fps 40
"""

import argparse
import csv
import sys


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path):
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rows.append({'t': fnum(r.get('t')), 'tdp': fnum(r.get('tdp_w')), 'fps': fnum(r.get('fps')),
                         'temp': fnum(r.get('temp_max')), 'pwm': fnum(r.get('fan_pwm')),
                         'rpm': fnum(r.get('fan_rpm'))})
    return [r for r in rows if r['t'] is not None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--target-fps', type=float, default=40.0)
    ap.add_argument('--deadband', type=float, default=2.0)
    args = ap.parse_args()

    rows = load(args.csv_path)
    if len(rows) < 10:
        print('Слишком мало строк для анализа:', len(rows))
        return 1

    goal = args.target_fps + 2.0
    changes = []          # (t, from, to)
    for i in range(1, len(rows)):
        a, b = rows[i - 1]['tdp'], rows[i]['tdp']
        if a is not None and b is not None and abs(b - a) >= 0.5:
            changes.append((rows[i]['t'], a, b))

    lowers = [c for c in changes if c[2] < c[1]]
    raises = [c for c in changes if c[2] > c[1]]

    # Провалы FPS за 5 с после снижения TDP: ниже цели-2
    drops = []
    for (tc, _, _) in lowers:
        window = [r['fps'] for r in rows if tc <= r['t'] <= tc + 5 and r['fps'] is not None]
        if window and min(window) < goal - args.deadband:
            drops.append((tc, round(min(window), 1)))

    # Время падения TDP: самый длинный участок, где FPS выше цели, до следующего снижения
    fall_times = []
    for i, (tc, fr, to) in enumerate(changes):
        if to < fr:
            prev = rows[max(0, i - 1)]
            fall_times.append((tc, fr, to))

    fps_vals = [r['fps'] for r in rows if r['fps'] is not None]
    below = sum(1 for f in fps_vals if f < goal - args.deadband)
    temps = [r['temp'] for r in rows if r['temp'] is not None]
    pwms = [r['pwm'] for r in rows if r['pwm'] is not None]
    rpm_changes = sum(1 for i in range(1, len(rows))
                      if rows[i]['rpm'] is not None and rows[i - 1]['rpm'] is not None
                      and rows[i]['rpm'] != rows[i - 1]['rpm'])
    pwm_changes = sum(1 for i in range(1, len(pwms)) if abs(pwms[i] - pwms[i - 1]) >= 1.0)

    print(f'Строк: {len(rows)}, длительность: {rows[-1]["t"]:.0f} с, цель: {goal:.0f} fps')
    print(f'Снижений TDP: {len(lowers)}, повышений: {len(raises)}')
    if lowers:
        sizes = [round(a - b, 1) for _, a, b in lowers]
        print(f'  размер снижений: {sizes[:15]}{" ..." if len(sizes) > 15 else ""}')
        print(f'  первый шаг вниз на {lowers[0][0]:.0f} с')
    print(f'Смен TDP всего: {len(changes)} (в среднем раз в {rows[-1]["t"] / max(1, len(changes)):.1f} с)')
    if fps_vals:
        print(f'FPS: средний {sum(fps_vals) / len(fps_vals):.1f}, ниже цели-{args.deadband:.0f}: '
              f'{below * 100.0 / len(fps_vals):.0f}% времени')
    if temps:
        print(f'Температура: максимум {max(temps):.1f} °C, средняя {sum(temps) / len(temps):.1f} °C')
    print(f'Вентилятор: изменений ШИМ {pwm_changes}, изменений оборотов {rpm_changes}')
    if drops:
        print(f'Провалы FPS после снижения TDP (ниже {goal - args.deadband:.0f}): {len(drops)}')
        for tc, f in drops[:10]:
            print(f'  t={tc:.0f} с, минимум {f} fps')
    else:
        print('Провалов FPS после снижения TDP не найдено')

    print()
    print('Что смотреть:')
    print('  * снижений должно быть немного (5–10 за прогон), а не десятки;')
    print('  * FPS ниже цели-2 — небольшая доля времени;')
    print('  * провалов после снижения быть не должно или они короткие;')
    print('  * изменений ШИМ должно быть заметно меньше, чем строк (гистерезис работает).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
