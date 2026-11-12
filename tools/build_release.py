#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Собирает установочный архив плагина для Decky Loader:
    release/GPD5CachyAutoTDP-<версия>-decky.zip

Внутри одна папка GPD5CachyAutoTDP/ с тем, что нужно плагину во время работы:
main.py, plugin.json, package.json, dist/index.js, backend/*.py, bin/README.txt,
tdp_gui.py и документы. Исходники интерфейса (src/), инструменты и конфиги сборки
в архив не входят.

Перед упаковкой dist/index.js пересобирается из src (npm run build), если не указан
--no-build. Версия берётся из plugin.json и сверяется с package.json и main.py.

Запуск из папки проекта:
    python3 tools/build_release.py
"""

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = ROOT / 'release'
PLUGIN_DIR_NAME = 'GPD5CachyAutoTDP'

TOP_FILES = [
    'README.md', 'README_RUS.md', 'CHANGELOG.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
    'SECURITY.md', '.gitignore', 'package.json', 'plugin.json', 'main.py', 'tdp_gui.py',
    'dist/index.js', 'bin/README.txt',
]
# Модули удалённых функций (2.3.0 и раньше): нигде не импортируются.
BACKEND_SKIP = {'core_evacuation.py', 'cpu_topology.py', 'fps_tdp_model.py'}


def fail(msg):
    print(f'Ошибка: {msg}', file=sys.stderr)
    sys.exit(1)


def read_version():
    plugin_v = json.loads((ROOT / 'plugin.json').read_text())['version']
    package_v = json.loads((ROOT / 'package.json').read_text())['version']
    if plugin_v != package_v:
        fail(f'версии расходятся: plugin.json {plugin_v}, package.json {package_v}')
    m = re.search(r"'build':'([^']+)'", (ROOT / 'main.py').read_text(encoding='utf-8'))
    if not m or m.group(1) != plugin_v:
        fail(f"строка сборки в main.py ({m.group(1) if m else 'не найдена'}) "
             f'не совпадает с plugin.json {plugin_v}')
    return plugin_v


def build_frontend():
    if not (ROOT / 'node_modules').exists():
        subprocess.run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=ROOT, check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=ROOT, check=True)


def collect_files():
    files = []
    for rel in TOP_FILES:
        path = ROOT / rel
        if not path.is_file():
            fail(f'нет файла {rel}')
        files.append(rel)
    for path in sorted((ROOT / 'backend').glob('*.py')):
        if path.name not in BACKEND_SKIP:
            files.append(f'backend/{path.name}')
    return files


def check_python(files):
    for rel in files:
        if rel.endswith('.py'):
            try:
                compile((ROOT / rel).read_text(encoding='utf-8'), rel, 'exec')
            except SyntaxError as e:
                fail(f'синтаксическая ошибка в {rel}: {e}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--no-build', action='store_true', help='не пересобирать dist/index.js')
    args = ap.parse_args()

    version = read_version()
    if not args.no_build:
        build_frontend()
    files = collect_files()
    check_python(files)

    RELEASE_DIR.mkdir(exist_ok=True)
    out = RELEASE_DIR / f'{PLUGIN_DIR_NAME}-{version}-decky.zip'
    tmp = out.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(ROOT / rel, f'{PLUGIN_DIR_NAME}/{rel}')
    tmp.replace(out)
    print(f'{out.relative_to(ROOT)}: {len(files)} файлов, {out.stat().st_size} байт')


if __name__ == '__main__':
    main()
