#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Сбор метрик для проверки на устройстве (этап 4 плана).

Пишет CSV с TDP, FPS, температурой, оборотами и решением контроллера, чтобы после игры
можно было посчитать: время падения TDP после снятия нагрузки, частоту проб вниз,
провалы FPS при пробах, поведение вентилятора.

Запуск на устройстве (root не обязателен для чтения, но нужен для части sysfs):
    sudo python3 tools/collect_metrics.py --seconds 300 --out /tmp/autotdp.csv

Источники:
  * TDP: /sys/class/firmware-attributes/amd_dptc/... или last setpoint из config.json;
  * FPS: самый новый mangoapp_*.csv из ~/.config/MangoHud или /tmp;
  * температура: /sys/class/hwmon/hwmon*/temp*_input (k10temp, zenpower, cpu_thermal);
  * вентилятор: pwm* и fan*_input там же.
Скрипт ничего не меняет в системе, только читает.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

HWMON = Path('/sys/class/hwmon')
DPTC_ATTRS = [Path('/sys/class/firmware-attributes/amd_dptc/attributes'),
              Path('/sys/class/firmware-attributes/amd-dptc/attributes')]
MANGOHUD_DIRS = [Path.home() / '.config/MangoHud', Path('/tmp')]


def read_tdp():
    for base in DPTC_ATTRS:
        for name in ('ppt_pl1_spl', 'stapm_limit'):
            p = base / name / 'current_value'
            if p.exists():
                try:
                    v = float(p.read_text().strip())
                    return v / 1000.0 if v > 1000 else v
                except (OSError, ValueError):
                    pass
    return None


def newest_mangohud():
    best, best_m = None, 0.0
    for d in MANGOHUD_DIRS:
        try:
            for p in d.glob('mangoapp_*.csv'):
                m = p.stat().st_mtime
                if m > best_m:
                    best, best_m = p, m
        except OSError:
            continue
    return best


def read_fps(path, last_pos):
    """Читает последнюю строку CSV MangoHud: fps = первая колонка."""
    if path is None:
        return None, last_pos
    try:
        size = path.stat().st_size
        if size < last_pos:          # файл пересоздан
            last_pos = 0
        with open(path, 'r', errors='ignore') as f:
            f.seek(last_pos)
            chunk = f.read()
            last_pos = f.tell()
        for line in reversed(chunk.strip().split('\n')):
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    return float(parts[0]), last_pos
                except ValueError:
                    continue
    except OSError:
        pass
    return None, last_pos


def read_temps():
    vals = {}
    try:
        for d in HWMON.glob('hwmon*'):
            try:
                name = (d / 'name').read_text().strip()
            except OSError:
                continue
            if name not in ('k10temp', 'zenpower', 'cpu_thermal'):
                continue
            for p in d.glob('temp*_input'):
                try:
                    vals[f'{name}:{p.name}'] = int(p.read_text()) / 1000.0
                except (OSError, ValueError):
                    continue
    except OSError:
        pass
    return vals


def read_fan():
    pwm, rpm = [], []
    try:
        for d in HWMON.glob('hwmon*'):
            try:
                name = (d / 'name').read_text().strip()
            except OSError:
                continue
            if name not in ('gpd_fan', 'gpd-fan', 'gpdfan'):
                continue
            for p in d.glob('pwm[0-9]*'):
                try:
                    pwm.append(round(int(p.read_text()) * 100.0 / 255.0, 1))
                except (OSError, ValueError):
                    pass
            for p in d.glob('fan[0-9]*_input'):
                try:
                    rpm.append(int(p.read_text()))
                except (OSError, ValueError):
                    pass
    except OSError:
        pass
    return pwm, rpm


def main():
    ap = argparse.ArgumentParser(description='Сбор метрик AutoTDP для проверки на устройстве')
    ap.add_argument('--seconds', type=float, default=300, help='длительность сбора, с')
    ap.add_argument('--interval', type=float, default=1.0, help='период опроса, с')
    ap.add_argument('--out', default='autotdp_metrics.csv', help='файл CSV')
    args = ap.parse_args()

    fields = ['t', 'tdp_w', 'fps', 'temp_max', 'fan_pwm', 'fan_rpm', 'mangohud']
    deadline = time.time() + args.seconds
    last_pos, mh, mh_seen = 0, None, 0.0
    rows = 0
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        t0 = time.time()
        while time.time() < deadline:
            now = time.time()
            # Файл MangoHud переискиваем не чаще раза в 5 с: новый файл появляется при перезапуске HUD.
            if mh is None or now - mh_seen > 5:
                found = newest_mangohud()
                if found is not None:
                    mh = found
                mh_seen = now
            fps, last_pos = read_fps(mh, last_pos)
            temps = read_temps()
            pwm, rpm = read_fan()
            w.writerow({
                't': round(time.time() - t0, 1),
                'tdp_w': read_tdp(),
                'fps': None if fps is None else round(fps, 1),
                'temp_max': max(temps.values()) if temps else None,
                'fan_pwm': pwm[0] if pwm else None,
                'fan_rpm': rpm[0] if rpm else None,
                'mangohud': str(mh) if mh else '',
            })
            f.flush()
            rows += 1
            time.sleep(max(0.1, args.interval))
    print(f'Записано {rows} строк в {args.out}')
    print('Как считать: см. tools/README.md')


if __name__ == '__main__':
    sys.exit(main())
