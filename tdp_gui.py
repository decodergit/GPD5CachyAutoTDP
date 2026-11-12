#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Настольный переключатель мощности чипа (Tk).

  * Ползунок задаёт лимит TDP от 5 до 80 Вт. Лимит применяется при отпускании ползунка
    (и при смещении клавишами стрелок), а не при каждом движении.
  * Выбранный лимит переписывается в систему каждые 5 секунд: так он не сбрасывается
    прошивкой или другим инструментом. Пока лимит не выбран, ничего не пишется.
  * Индикатор показывает реальную мощность чипа по счётчику энергии powercap/RAPL.
    Если счётчика нет, показывается «нет данных», а не выдуманное число.
  * Вентилятор: режимы «Авто (прошивка)», «Кривая» (кривая из backend) и «Вручную»
    (ползунок скорости). При закрытии окна управление возвращается прошивке.
  * Настройки (лимит TDP, режим и ручная скорость вентилятора) сохраняются в
    ~/.config/gpd5-tdp-gui.json пользователя, запустившего окно, и применяются
    при следующем запуске.
  * Плагин Decky на время работы окна полностью приостанавливается: окно пишет свой PID
    в /run/gpd5cachyautotdp/gui.pid, плагин останавливает AutoTDP и кривую вентилятора и
    отвечает в plugin.json. Пока плагин не ответил (до 8 с), окно ничего не пишет.
    При закрытии окна (или его падении) плагин возвращается в прежнее состояние.
  * Права администратора: если скрипт запущен не от root, он перезапускает себя через sudo.
    Пароль sudo спрашивается в диалоге только в первый раз и когда сохранённый не подошёл.
    Он хранится в системном хранилище паролей (Secret Service: KDE Wallet / GNOME Keyring)
    через `secret-tool`, а не в файле. Если хранилища нет, пароль спрашивается каждый раз.
    Пароль передаётся только через stdin (`sudo -S -v`, `secret-tool store`), в командной
    строке его нет.

Запуск из папки проекта:
    python3 tdp_gui.py
"""

import atexit
import json
import os
import pwd
import shutil
import signal
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

MIN_W = 5
MAX_W = 80
POLL_MS = 1000
REAPPLY_MS = 5000
ELEVATED_FLAG = '--elevated'
POWERCAP_ROOTS = [Path('/sys/class/powercap')]
PLUGIN_WAIT_MS = 8000      # сколько ждать, пока плагин Decky остановится
PLUGIN_POLL_MS = 250

# ---------------------------------------------------------------- настройки

SETTINGS_NAME = 'gpd5-tdp-gui.json'


def real_user():
    """(home, uid, gid) пользователя, запустившего окно, даже если оно работает через sudo."""
    uid = os.environ.get('SUDO_UID')
    if uid and uid.isdigit():
        try:
            pw = pwd.getpwuid(int(uid))
            return Path(pw.pw_dir), pw.pw_uid, pw.pw_gid
        except KeyError:
            pass
    return Path.home(), os.getuid(), os.getgid()


def settings_path():
    home, _, _ = real_user()
    return home / '.config' / SETTINGS_NAME


def load_settings(path=None):
    """Словарь сохранённых настроек; при отсутствии или порче файла — пустой."""
    path = path or settings_path()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data, path=None):
    """Атомарно пишет настройки и отдаёт файл пользователю, а не root."""
    path = path or settings_path()
    _, uid, gid = real_user()
    tmp = path.with_suffix(path.suffix + '.tmp')
    try:
        created_dir = not path.parent.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        if created_dir and os.geteuid() == 0:
            os.chown(path.parent, uid, gid)
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        if os.geteuid() == 0:
            os.chown(tmp, uid, gid)
        os.replace(tmp, path)
    except OSError as e:
        print(f'Не удалось сохранить настройки {path}: {e}', file=sys.stderr)
        return False
    return True

# ---------------------------------------------------------------- энергия чипа

def find_energy_counters():
    """Возвращает [(путь к energy_uj, max_energy_range_uj)] только для доменов пакета CPU."""
    found = []
    for root in POWERCAP_ROOTS:
        if not root.exists():
            continue
        for dom in sorted(root.glob('*')):
            energy = dom / 'energy_uj'
            if not energy.exists():
                continue
            name = ''
            try:
                name = (dom / 'name').read_text().strip()
            except OSError:
                pass
            if name and 'package' not in name and 'psys' not in name:
                continue  # ядра и DRAM не складываем с пакетом
            max_range = 0
            try:
                max_range = int((dom / 'max_energy_range_uj').read_text())
            except (OSError, ValueError):
                pass
            found.append((energy, max_range))
    return found

class PowerReader:
    """Средняя мощность (Вт) между двумя опросами по приращению счётчика энергии."""

    def __init__(self):
        self.counters = find_energy_counters()
        self._last = None  # (время, [значения energy_uj])

    @property
    def available(self):
        return bool(self.counters)

    def _read_all(self):
        values = []
        for path, _ in self.counters:
            try:
                values.append(int(path.read_text()))
            except (OSError, ValueError):
                return None
        return values

    def sample(self):
        if not self.counters:
            return None
        now = time.monotonic()
        values = self._read_all()
        if values is None:
            self._last = None
            return None
        result = None
        if self._last is not None:
            dt = now - self._last[0]
            if dt > 0:
                total_uj = 0
                for cur, prev, (_, max_range) in zip(values, self._last[1], self.counters):
                    delta = cur - prev
                    if delta < 0:  # счётчик переполнился
                        delta += max_range if max_range else 0
                    total_uj += max(0, delta)
                result = total_uj / 1_000_000.0 / dt
        self._last = (now, values)
        return result

# ---------------------------------------------------------------- лимит TDP

def load_backend():
    """(TDPController, ''), либо (None, причина)."""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        from backend.tdp_controller import TDPController
    except Exception as e:  # noqa: BLE001
        return None, f'Не удалось загрузить backend: {e}'
    try:
        ctl = TDPController()
    except Exception as e:  # noqa: BLE001
        return None, f'Не удалось инициализировать TDP backend: {e}'
    if not ctl.available():
        return None, 'Реальный TDP backend не найден (нет DPTC и ryzenadj).'
    return ctl, ''

def clamp_limit(watts):
    return int(max(MIN_W, min(MAX_W, round(float(watts)))))

class LimitKeeper:
    """Хранит выбранный лимит и записывает его в backend.

    apply() вызывается при отпускании ползунка и каждые REAPPLY_MS из окна.
    Пока лимит не задан (target_w is None), ничего не пишется.
    """

    def __init__(self, ctl):
        self.ctl = ctl
        self.target_w = None
        self.last_ok = None
        self.last_error = ''

    def set_target(self, watts):
        self.target_w = clamp_limit(watts)
        return self.apply()

    def apply(self):
        if self.target_w is None:
            return None
        if self.ctl is None:
            self.last_ok = False
            self.last_error = 'нет backend'
            return False
        try:
            ok = bool(self.ctl.set_tdp(float(self.target_w)))
        except Exception as e:  # noqa: BLE001
            ok = False
            self.last_error = str(e)
        else:
            self.last_error = '' if ok else 'backend не принял значение'
        self.last_ok = ok
        return ok

# ---------------------------------------------------------------- права администратора

def needs_elevation(argv, euid):
    return euid != 0 and ELEVATED_FLAG not in argv


def build_elevated_command(script_path, python, display, xauthority):
    """Команда повторного запуска от root. Пароль сюда не попадает.

    `sudo -n` использует уже подтверждённый пароль (кеш sudo после `sudo -v`),
    `env` переносит DISPLAY и XAUTHORITY, чтобы окно открылось в сессии пользователя.
    """
    cmd = ['sudo', '-n', 'env']
    if display:
        cmd.append(f'DISPLAY={display}')
    if xauthority:
        cmd.append(f'XAUTHORITY={xauthority}')
    cmd += [python, str(script_path), ELEVATED_FLAG]
    return cmd


KEYRING_ATTRS = ['application', 'gpd5-tdp-gui', 'purpose', 'sudo']
KEYRING_LABEL = 'GPD5 TDP GUI: пароль sudo'
MAX_PASSWORD_TRIES = 3


def _keyring_attrs():
    import getpass
    return KEYRING_ATTRS + ['user', getpass.getuser()]


def keyring_available():
    return shutil.which('secret-tool') is not None


def keyring_get():
    """Сохранённый пароль или None (нет хранилища, нет записи, кошелёк не открыт)."""
    if not keyring_available():
        return None
    try:
        r = subprocess.run(['secret-tool', 'lookup', *_keyring_attrs()],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    return r.stdout.rstrip('\n')


def keyring_store(password):
    if not keyring_available():
        return False
    try:
        r = subprocess.run(['secret-tool', 'store', '--label', KEYRING_LABEL, *_keyring_attrs()],
                           input=password, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def keyring_clear():
    if not keyring_available():
        return
    try:
        subprocess.run(['secret-tool', 'clear', *_keyring_attrs()],
                       capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass


def sudo_cached():
    """True, если sudo уже не требует пароль (свежий кеш или NOPASSWD)."""
    try:
        return subprocess.run(['sudo', '-n', 'true'], capture_output=True,
                              timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def sudo_validate(password):
    try:
        r = subprocess.run(['sudo', '-S', '-p', '', '-v'], input=password + '\n',
                           text=True, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0


def ask_password(parent, note=''):
    text = 'Для управления TDP нужны права администратора.\n'
    if note:
        text += note + '\n'
    if keyring_available():
        text += 'Пароль будет сохранён в системном хранилище паролей.\n'
    else:
        text += 'secret-tool не найден: пароль не сохраняется.\n'
    text += 'Введите пароль sudo:'
    return simpledialog.askstring('Права администратора', text, show='*', parent=parent)


def obtain_sudo(parent):
    """Подтверждает sudo: кеш, затем сохранённый пароль, затем диалог.

    Возвращает True, если sudo готов к `sudo -n`.
    """
    if sudo_cached():
        return True
    password = keyring_get()
    if password is not None:
        if sudo_validate(password):
            return True
        keyring_clear()  # сохранённый пароль устарел
        note = 'Сохранённый пароль не подошёл.'
    else:
        note = ''
    for _ in range(MAX_PASSWORD_TRIES):
        password = ask_password(parent, note)
        if password is None:
            return False
        if sudo_validate(password):
            if not keyring_store(password) and keyring_available():
                messagebox.showwarning('Пароль', 'Не удалось сохранить пароль в хранилище: '
                                       'в следующий раз он будет запрошен снова.', parent=parent)
            return True
        note = 'Пароль не подошёл, попробуйте ещё раз.'
    messagebox.showerror('sudo', 'Пароль не принят или sudo недоступен.', parent=parent)
    return False


def relaunch_as_root(argv):
    """Подтверждает sudo (кеш, сохранённый пароль или диалог) и запускает окно от root.

    Возвращает код выхода для процесса, который пользователь запустил.
    """
    if shutil.which('sudo') is None:
        print('Нужен sudo, но он не найден.', file=sys.stderr)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print(f'Нет графического дисплея: {e}', file=sys.stderr)
        return 1
    root.withdraw()
    ok = obtain_sudo(root)
    root.destroy()
    if not ok:
        return 1

    cmd = build_elevated_command(
        Path(__file__).resolve(), sys.executable,
        os.environ.get('DISPLAY', ''),
        os.environ.get('XAUTHORITY', str(Path.home() / '.Xauthority')),
    )
    rc = subprocess.run(cmd + list(argv)).returncode
    if rc != 0:
        err = tk.Tk()
        err.withdraw()
        messagebox.showerror('sudo', 'Не удалось запустить окно от администратора.\n'
                                 'Проверьте, что sudo разрешает запуск без повторного пароля '
                                 'сразу после подтверждения (timestamp_timeout).', parent=err)
        err.destroy()
    return rc

# ---------------------------------------------------------------- вентилятор

FAN_MODES = (('auto', 'Авто (прошивка)'), ('curve', 'Кривая'), ('manual', 'Вручную'))


def load_fan_controller():
    """(FanController, '') или (None, причина)."""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        from backend.fan_controller import FanController
    except Exception as e:  # noqa: BLE001
        return None, f'Не удалось загрузить управление вентилятором: {e}'
    try:
        fan = FanController()
    except Exception as e:  # noqa: BLE001
        return None, f'Не удалось инициализировать вентилятор: {e}'
    if not fan.is_available():
        return None, 'Вентилятор или датчик температуры не найден.'
    return fan, ''


def load_gui_lock():
    """Модуль backend.gui_lock или None."""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        from backend import gui_lock
    except Exception:  # noqa: BLE001
        return None
    return gui_lock


class FanKeeper:
    """Режим вентилятора: прошивка, кривая из backend или ручная скорость.

    Ручная скорость переписывается вместе с лимитом TDP каждые REAPPLY_MS,
    чтобы прошивка её не перехватила.
    """

    def __init__(self, fan):
        self.fan = fan
        self.mode = 'auto'
        self.manual_pct = 50
        self.last_ok = None
        self.last_error = ''

    def _stop_curve(self):
        f = self.fan
        f.enabled = False
        f._stop.set()
        if f._thread and f._thread.is_alive():
            f._thread.join(2)
        f._applied_pct = None
        f._target_pct = None
        f._last_temp = None

    def set_mode(self, mode):
        self.mode = mode
        try:
            if mode == 'auto':
                self.last_ok = bool(self.fan.disable())
            elif mode == 'curve':
                self.last_ok = bool(self.fan.enable())
            else:
                self._stop_curve()
                self.fan._mode(True)
                self.last_ok = bool(self.fan.set_fan_speed(self.manual_pct))
        except Exception as e:  # noqa: BLE001
            self.last_ok = False
            self.last_error = str(e)
        else:
            self.last_error = '' if self.last_ok else 'запись в sysfs не удалась'
        return self.last_ok

    def set_manual(self, pct):
        self.manual_pct = int(max(0, min(100, round(float(pct)))))
        if self.mode == 'manual':
            return self.reapply()
        return None

    def reapply(self):
        if self.mode != 'manual':
            return None
        try:
            self.fan._mode(True)
            self.last_ok = bool(self.fan.set_fan_speed(self.manual_pct))
        except Exception as e:  # noqa: BLE001
            self.last_ok = False
            self.last_error = str(e)
        else:
            self.last_error = '' if self.last_ok else 'запись в sysfs не удалась'
        return self.last_ok

    def release(self):
        """Возвращает вентилятор прошивке (при закрытии окна)."""
        try:
            self.fan.disable()
        except Exception:  # noqa: BLE001
            pass

    def sample(self):
        """(скважность %, температура °C, обороты)."""
        stats = self.fan.get_stats()
        pwm = [v for v in stats.get('pwm_percent', []) if v is not None]
        rpm = [v for v in stats.get('fan_rpm', []) if v is not None]
        return (pwm[0] if pwm else None,
                stats.get('current_temperature'),
                rpm[0] if rpm else None)

# ---------------------------------------------------------------- окно

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Лимит мощности чипа')
        self.resizable(False, False)
        self.reader = PowerReader()
        self.ctl, self.backend_error = load_backend()
        self.keeper = LimitKeeper(self.ctl)
        fan, self.fan_error = load_fan_controller()
        self.fan = FanKeeper(fan) if fan else None
        self.settings = load_settings()

        self.limit_var = tk.IntVar(value=35)
        self.limit_text_var = tk.StringVar(value='35 Вт')
        self.power_var = tk.StringVar(value='—')
        self.status_var = tk.StringVar(value='')
        self.fan_mode_var = tk.StringVar(value='auto')
        self.fan_pct_var = tk.IntVar(value=50)
        self.fan_pct_text_var = tk.StringVar(value='50 %')
        self.fan_now_var = tk.StringVar(value='—')
        self.fan_status_var = tk.StringVar(value='')

        self.ready = False          # True, когда плагин Decky отпустил TDP и вентилятор
        self.plugin_note = 'Ожидание остановки плагина Decky…'
        self._controls = []
        self._closed = False

        self._build()
        self._read_initial_limit()
        self._set_controls_enabled(False)
        self._update_status()
        self._update_fan_status()
        self._tick()
        if self.fan:
            self._tick_fan()
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self._suspend_plugin()

    # --- плагин Decky
    def _suspend_plugin(self):
        self.gui_lock = load_gui_lock()
        if self.gui_lock is None:
            self.plugin_note = 'Модуль связи с плагином не найден: плагин Decky не приостановлен.'
            self._become_ready()
            return
        try:
            self.gui_lock.acquire()
        except OSError as e:
            self.plugin_note = f'Не удалось приостановить плагин Decky: {e}'
            self._become_ready()
            return
        atexit.register(self._release_plugin)
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, lambda *_: self.after(0, self._on_close))
        self._wait_started = time.monotonic()
        self._wait_plugin()

    def _wait_plugin(self):
        st = self.gui_lock.plugin_state()
        if st is None:
            self.plugin_note = 'Плагин Decky не запущен.'
        elif not st.get('active', True):
            self.plugin_note = 'Плагин Decky приостановлен, пока открыто окно.'
        elif (time.monotonic() - self._wait_started) * 1000 < PLUGIN_WAIT_MS:
            self.after(PLUGIN_POLL_MS, self._wait_plugin)
            return
        else:
            self.plugin_note = ('Плагин Decky не остановился за '
                                f'{PLUGIN_WAIT_MS // 1000} с: возможен конфликт. '
                                'Обновите плагин или выключите его вручную.')
        self._become_ready()

    def _become_ready(self):
        self.ready = True
        self._set_controls_enabled(True)
        self._restore_settings()
        self._update_status()
        self._update_fan_status()
        self.after(REAPPLY_MS, self._reapply)

    def _release_plugin(self):
        gl = getattr(self, 'gui_lock', None)
        if gl is not None:
            gl.release()

    def _set_controls_enabled(self, on):
        state = 'normal' if on else 'disabled'
        self.slider.configure(state=state)
        for w in self._controls:
            w.state(['!disabled'] if on else ['disabled'])
        if self.fan:
            self._sync_fan_slider_state()

    def _build(self):
        pad = {'padx': 14, 'pady': 6}
        bold = ('TkDefaultFont', 11, 'bold')
        frame = ttk.Frame(self, padding=8)
        frame.grid(sticky='nsew')
        frame.columnconfigure(0, weight=1)
        row = 0

        def place(widget, **kw):
            nonlocal row
            opts = {'row': row, 'column': 0, 'sticky': 'w', **pad}
            opts.update(kw)
            widget.grid(**opts)
            row += 1
            return widget

        def separator():
            place(ttk.Separator(frame, orient='horizontal'), sticky='we', padx=4, pady=10)

        # --- мощность
        place(ttk.Label(frame, text='Реальная мощность чипа', font=bold))
        place(ttk.Label(frame, textvariable=self.power_var, font=('TkDefaultFont', 28, 'bold')))
        self.bar = place(ttk.Progressbar(frame, length=320, maximum=MAX_W, mode='determinate'),
                         sticky='we')

        separator()

        # --- лимит TDP
        place(ttk.Label(frame, text='Ограничение (лимит) TDP', font=bold))
        self.slider = place(tk.Scale(frame, from_=MIN_W, to=MAX_W, orient='horizontal', length=320,
                                     variable=self.limit_var, showvalue=False,
                                     command=self._on_drag), sticky='we')
        # Применяем при отпускании мыши и клавишах, а не при каждом движении
        self.slider.bind('<ButtonRelease-1>', self._on_release)
        self.slider.bind('<KeyRelease>', self._on_release)
        place(ttk.Label(frame, textvariable=self.limit_text_var, font=('TkDefaultFont', 12)))

        separator()

        # --- вентилятор
        place(ttk.Label(frame, text='Вентилятор', font=bold))
        if self.fan:
            place(ttk.Label(frame, textvariable=self.fan_now_var, font=('TkDefaultFont', 16, 'bold')))
            modes = ttk.Frame(frame)
            for i, (key, title) in enumerate(FAN_MODES):
                rb = ttk.Radiobutton(modes, text=title, value=key, variable=self.fan_mode_var,
                                     command=self._on_fan_mode)
                rb.grid(row=0, column=i, padx=(0, 12))
                self._controls.append(rb)
            place(modes)
            self.fan_slider = place(tk.Scale(frame, from_=0, to=100, orient='horizontal', length=320,
                                             variable=self.fan_pct_var, showvalue=False,
                                             command=self._on_fan_drag), sticky='we')
            self.fan_slider.bind('<ButtonRelease-1>', self._on_fan_release)
            self.fan_slider.bind('<KeyRelease>', self._on_fan_release)
            place(ttk.Label(frame, textvariable=self.fan_pct_text_var, font=('TkDefaultFont', 12)))
            self._sync_fan_slider_state()
        place(ttk.Label(frame, textvariable=self.fan_status_var, wraplength=360, foreground='#555'))

        separator()

        place(ttk.Label(frame, textvariable=self.status_var, wraplength=360, foreground='#555'))

    # --- настройки
    def _restore_settings(self):
        """Применяет сохранённые лимит и режим вентилятора."""
        s = self.settings
        try:
            tdp = s.get('tdp_w')
            if tdp is not None:
                value = clamp_limit(tdp)
                self.limit_var.set(value)
                self.limit_text_var.set(f'{value} Вт')
                self.keeper.set_target(value)
        except (TypeError, ValueError):
            pass
        if not self.fan:
            return
        try:
            pct = int(max(0, min(100, round(float(s.get('fan_manual_pct', 50))))))
        except (TypeError, ValueError):
            pct = 50
        self.fan.manual_pct = pct
        self.fan_pct_var.set(pct)
        self.fan_pct_text_var.set(f'{pct} %')
        mode = s.get('fan_mode', 'auto')
        if mode not in dict(FAN_MODES):
            mode = 'auto'
        self.fan_mode_var.set(mode)
        if mode != 'auto':
            self.fan.set_mode(mode)
        self._sync_fan_slider_state()

    def _save_settings(self):
        data = dict(self.settings)
        if self.keeper.target_w is not None:
            data['tdp_w'] = self.keeper.target_w
        if self.fan:
            data['fan_mode'] = self.fan.mode
            data['fan_manual_pct'] = self.fan.manual_pct
        if data != self.settings and save_settings(data):
            self.settings = data

    # --- TDP
    def _read_initial_limit(self):
        """Показываем текущую уставку, но ничего не пишем."""
        if self.ctl is None:
            return
        try:
            cur = self.ctl.read_tdp()
        except Exception:  # noqa: BLE001
            cur = None
        if cur is None:
            return
        value = clamp_limit(cur)
        self.limit_var.set(value)
        self.limit_text_var.set(f'{value} Вт')

    def _on_drag(self, value):
        self.limit_text_var.set(f'{int(float(value))} Вт')

    def _on_release(self, _event=None):
        if not self.ready:
            return
        self.keeper.set_target(self.limit_var.get())
        self._update_status()
        self._save_settings()

    def _reapply(self):
        if self.keeper.target_w is not None:
            self.keeper.apply()
            self._update_status()
        if self.fan and self.fan.mode == 'manual':
            self.fan.reapply()
            self._update_fan_status()
        self.after(REAPPLY_MS, self._reapply)

    def _update_status(self):
        lines = []
        if self.ctl is None:
            lines.append(self.backend_error)
        else:
            lines.append(f'Backend: {self.ctl.backend}')
        if self.keeper.target_w is None:
            lines.append('Лимит ещё не задан: перетащите ползунок.')
        elif self.keeper.last_ok:
            lines.append(f'Лимит {self.keeper.target_w} Вт записан, переписывается каждые '
                         f'{REAPPLY_MS // 1000} с.')
        else:
            lines.append(f'Лимит {self.keeper.target_w} Вт НЕ записан: {self.keeper.last_error}')
        if not self.reader.available:
            lines.append('Счётчик энергии (powercap/RAPL) не найден: мощность не измеряется.')
        else:
            lines.append('Измерение мощности работает.')
        lines.append(self.plugin_note)
        self.status_var.set('\n'.join(lines))

    def _tick(self):
        p = self.reader.sample()
        if p is None:
            self.power_var.set('нет данных')
            self.bar.configure(value=0)
        else:
            self.power_var.set(f'{p:5.1f} Вт')
            self.bar.configure(value=max(0, min(MAX_W, p)))
        self.after(POLL_MS, self._tick)

    # --- вентилятор
    def _sync_fan_slider_state(self):
        on = self.ready and self.fan_mode_var.get() == 'manual'
        self.fan_slider.configure(state='normal' if on else 'disabled')

    def _on_fan_mode(self):
        self.fan.set_mode(self.fan_mode_var.get())
        self._sync_fan_slider_state()
        self._update_fan_status()
        self._save_settings()

    def _on_fan_drag(self, value):
        self.fan_pct_text_var.set(f'{int(float(value))} %')

    def _on_fan_release(self, _event=None):
        if not self.ready or self.fan_mode_var.get() != 'manual':
            return
        self.fan.set_manual(self.fan_pct_var.get())
        self._update_fan_status()
        self._save_settings()

    def _update_fan_status(self):
        if not self.fan:
            self.fan_status_var.set(self.fan_error)
            return
        f = self.fan
        if f.mode == 'auto':
            text = 'Скоростью управляет прошивка.'
        elif f.mode == 'curve':
            text = 'Скорость задаёт кривая температуры (как в плагине).'
        else:
            text = f'Ручная скорость {f.manual_pct} %, переписывается каждые {REAPPLY_MS // 1000} с.'
        if f.last_ok is False:
            text += f'\nНе удалось применить: {f.last_error}'
        text += '\nПри закрытии окна вентилятор возвращается прошивке.'
        self.fan_status_var.set(text)

    def _tick_fan(self):
        try:
            pct, temp, rpm = self.fan.sample()
        except Exception:  # noqa: BLE001
            pct = temp = rpm = None
        parts = [f'{temp:.0f} °C' if temp is not None else '— °C',
                 f'{pct:.0f} %' if pct is not None else '— %',
                 f'{rpm} об/мин' if rpm is not None else '— об/мин']
        self.fan_now_var.set('   '.join(parts))
        self.after(POLL_MS, self._tick_fan)

    def _on_close(self):
        if self._closed:
            return
        self._closed = True
        if self.ready:
            self._save_settings()
        if self.fan:
            self.fan.release()
        # Блокировку снимаем последней: плагин включит свою кривую уже после
        # того, как окно вернуло вентилятор прошивке.
        self._release_plugin()
        self.destroy()

# ---------------------------------------------------------------- main

def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if sys.platform.startswith('win'):
        print('Скрипт рассчитан на Linux (CachyOS).')
        return 1
    if needs_elevation(argv, os.geteuid()):
        return relaunch_as_root(argv)
    App().mainloop()
    return 0

if __name__ == '__main__':
    sys.exit(main())
