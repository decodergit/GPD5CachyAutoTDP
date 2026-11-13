// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
// Словарь интерфейса. Ключи должны совпадать для en и ru.
// 3.7.0: короткие формулировки; подробности — в README.

export type Lang = 'en' | 'ru';

export const DICT: Record<Lang, Record<string, string>> = {
  en: {
    'unit.w': 'W',
    'status.connecting': 'Connecting to backend…',

    // главные переключатели
    'toggle.plugin': 'Plugin enabled',
    'toggle.plugin.on': 'Controls TDP and fan',
    'toggle.plugin.off': 'Fully off: TDP and fan are not touched',
    'toggle.plugin.gui': 'Paused while the tdp_gui.py window is open',
    'toggle.autotdp': 'Auto TDP',
    'toggle.autotdp.on': 'Holds the target FPS at the lowest TDP',
    'toggle.autotdp.off': 'TDP stays at the start value',

    // сводка
    'sum.fps': 'FPS',
    'sum.tdp': 'TDP',
    'sum.temp': 'Temp',
    'sum.goal': 'goal {0}',
    'phase.holding': 'Holding the target',
    'phase.raising': 'Raising TDP: FPS is short',
    'phase.lowering': 'Lowering TDP: FPS to spare',
    'phase.probing': 'Looking for the lowest TDP',
    'phase.short': 'FPS is short at the TDP limit',
    'phase.boost': 'High-load boost',
    'phase.waiting': 'Waiting for FPS from MangoHud',
    'phase.off': 'Auto TDP is off',
    'chart.legend': 'last minute',
    'game.levels': 'levels {0} W',
    'game.unknown': 'Game not detected',
    'display.handheld': 'handheld {0}',
    'display.external': 'external {0}',
    'warn.noFps': 'No FPS from MangoHud. Keep MangoHud enabled and turn FPS limits off in the game and in gamescope.',

    // настройки
    'slider.targetFps': 'Target FPS',
    'fold.limits': 'TDP limits · {0}–{1} W',
    'fold.advanced': 'More settings',
    'fold.diag': 'Diagnostics',
    'slider.minTdp': 'Minimum TDP',
    'slider.maxTdp': 'Maximum TDP',
    'slider.startTdp': 'Start TDP',
    'slider.startTdp.on': 'Used when Auto TDP starts',
    'slider.startTdp.off': 'Applied now: Auto TDP is off',
    'toggle.loadBoost': 'High-load boost',
    'toggle.loadBoost.on': 'CPU >{0}% always, GPU >{0}% when FPS is short',
    'toggle.loadBoost.off': 'Off',
    'slider.threshold': 'High-load threshold',
    'slider.interval': 'Poll interval',
    'slider.interval.desc': '1 s is a good default',
    'src.hud': 'Show MangoHud',
    'src.hud.on': 'Overlay visible',
    'src.hud.off': 'Overlay hidden, FPS is still logged',
    'lang.title': 'Language',
    'lang.auto': 'Auto (Steam language)',
    'lang.en': 'English',
    'lang.ru': 'Русский',

    // вентилятор
    'section.fan': 'Fan',
    'fan.control': 'Fan curve',
    'fan.control.on': 'The plugin drives the fan',
    'fan.control.off': 'Firmware drives the fan',
    'fan.caption': '{0} °C · {1} % · {2} rpm',
    'fan.notDetected': 'PWM fan controller not detected.',

    // диагностика
    'row.build': 'Build',
    'row.build.old': 'old backend: reinstall the archive',
    'row.tdpBackend': 'TDP backend',
    'row.tdpSource': 'TDP source',
    'row.tdpSource.setpoint': 'setpoint (no readback)',
    'row.tdpDecision': 'TDP decision',
    'row.tdpCapped': 'capped at {0} W',
    'row.controller': 'Controller',
    'row.controller.stopped': 'stopped',
    'search.state': 'Search',
    'search.state.idle': 'not started',
    'search.state.probing': 'testing a level',
    'search.state.searching': 'narrowing the range',
    'search.state.done': 'minimum found',
    'search.good': 'Holds the target at',
    'search.bad': 'Short of the target at',
    'search.probes': 'Tries',
    'search.unknown': '—',
    'row.cpuLoad': 'CPU load',
    'row.gpuLoad': 'GPU load',
    'src.source': 'FPS source',
    'src.sourceDefault': 'MangoHud CSV',
    'fan.controller': 'Fan controller',
    'fan.controller.ok': 'gpdfan, {0} channel(s)',
    'fan.controller.none': 'not detected',

    // редактор кривой
    'curve.title': 'Fan curve',
    'curve.temp': 'Temp, °C',
    'curve.speed': 'Speed, %',
    'curve.edit': 'Edit curve',
    'curve.graphHint': 'Drag a point to move it, tap empty space to add one.',
    'curve.prev': '◀ Point',
    'curve.next': 'Point ▶',
    'curve.selected': 'Point {0} of {1}: {2} °C → {3} %',
    'curve.delete': 'Delete point',
    'curve.reset': 'Default curve',
    'curve.save': 'Save',
    'curve.cancel': 'Cancel',
    'curve.saved': 'Curve saved',
    'curve.saveFail': 'Curve rejected: {0}',

    // ошибки
    'init.title': 'Initialization error',
    'err.getConfig': 'Backend returned an invalid config: {0}',
    'err.getStats': 'Backend does not respond',
    'err.backend': 'Backend: {0}',
    'err.save': 'Backend did not accept the change',
    'err.params': 'Backend did not accept the Auto TDP settings',
    'err.toggle': 'Could not switch Auto TDP',
    'err.plugin': 'Could not switch the plugin',
    'err.lang': 'Could not save the language',
  },
  ru: {
    'unit.w': 'Вт',
    'status.connecting': 'Подключение к backend…',

    'toggle.plugin': 'Плагин включён',
    'toggle.plugin.on': 'Управляет TDP и вентилятором',
    'toggle.plugin.off': 'Полностью отключён: TDP и вентилятор не трогаются',
    'toggle.plugin.gui': 'Приостановлен, пока открыто окно tdp_gui.py',
    'toggle.autotdp': 'Auto TDP',
    'toggle.autotdp.on': 'Держит целевой FPS на минимальном TDP',
    'toggle.autotdp.off': 'TDP стоит на стартовом значении',

    'sum.fps': 'FPS',
    'sum.tdp': 'TDP',
    'sum.temp': 'Темп.',
    'sum.goal': 'цель {0}',
    'phase.holding': 'Цель держится',
    'phase.raising': 'Поднимает TDP: не хватает кадров',
    'phase.lowering': 'Снижает TDP: есть запас кадров',
    'phase.probing': 'Ищет минимальный TDP',
    'phase.short': 'Не хватает кадров на пределе TDP',
    'phase.boost': 'Буст при высокой нагрузке',
    'phase.waiting': 'Ждёт FPS от MangoHud',
    'phase.off': 'Auto TDP выключен',
    'chart.legend': 'последняя минута',
    'game.levels': 'уровни {0} Вт',
    'game.unknown': 'Игра не определена',
    'display.handheld': 'в руках {0}',
    'display.external': 'внешний экран {0}',
    'warn.noFps': 'Нет FPS от MangoHud. Оставьте MangoHud включённым и снимите ограничение FPS в игре и в gamescope.',

    'slider.targetFps': 'Целевой FPS',
    'fold.limits': 'Лимиты TDP · {0}–{1} Вт',
    'fold.advanced': 'Дополнительно',
    'fold.diag': 'Диагностика',
    'slider.minTdp': 'Минимальный TDP',
    'slider.maxTdp': 'Максимальный TDP',
    'slider.startTdp': 'Стартовый TDP',
    'slider.startTdp.on': 'С него начинает Auto TDP',
    'slider.startTdp.off': 'Применяется сразу: Auto TDP выключен',
    'toggle.loadBoost': 'Буст при высокой нагрузке',
    'toggle.loadBoost.on': 'CPU >{0}% всегда, GPU >{0}% при нехватке FPS',
    'toggle.loadBoost.off': 'Выключен',
    'slider.threshold': 'Порог высокой нагрузки',
    'slider.interval': 'Интервал опроса',
    'slider.interval.desc': '1 с — хороший выбор',
    'src.hud': 'Показывать MangoHud',
    'src.hud.on': 'Оверлей виден',
    'src.hud.off': 'Оверлей скрыт, FPS пишется в лог',
    'lang.title': 'Язык',
    'lang.auto': 'Авто (язык Steam)',
    'lang.en': 'English',
    'lang.ru': 'Русский',

    'section.fan': 'Вентилятор',
    'fan.control': 'Кривая вентилятора',
    'fan.control.on': 'Вентилятором управляет плагин',
    'fan.control.off': 'Вентилятором управляет прошивка',
    'fan.caption': '{0} °C · {1} % · {2} об/мин',
    'fan.notDetected': 'Контроллер PWM-вентилятора не обнаружен.',

    'row.build': 'Сборка',
    'row.build.old': 'старый backend: переустановите архив',
    'row.tdpBackend': 'Бэкенд TDP',
    'row.tdpSource': 'Источник TDP',
    'row.tdpSource.setpoint': 'заданное (без чтения)',
    'row.tdpDecision': 'Решение по TDP',
    'row.tdpCapped': 'ограничено {0} Вт',
    'row.controller': 'Контроллер',
    'row.controller.stopped': 'остановлен',
    'search.state': 'Поиск',
    'search.state.idle': 'не начат',
    'search.state.probing': 'проверка уровня',
    'search.state.searching': 'сужение отрезка',
    'search.state.done': 'минимум найден',
    'search.good': 'Держит цель на',
    'search.bad': 'Ниже цели на',
    'search.probes': 'Проб',
    'search.unknown': '—',
    'row.cpuLoad': 'Загрузка CPU',
    'row.gpuLoad': 'Загрузка GPU',
    'src.source': 'Источник FPS',
    'src.sourceDefault': 'CSV MangoHud',
    'fan.controller': 'Контроллер вентилятора',
    'fan.controller.ok': 'gpdfan, каналов: {0}',
    'fan.controller.none': 'не обнаружен',

    'curve.title': 'Кривая вентилятора',
    'curve.temp': 'Температура, °C',
    'curve.speed': 'Скорость, %',
    'curve.edit': 'Изменить кривую',
    'curve.graphHint': 'Перетащите точку, чтобы сдвинуть её; коснитесь пустого места, чтобы добавить.',
    'curve.prev': '◀ Точка',
    'curve.next': 'Точка ▶',
    'curve.selected': 'Точка {0} из {1}: {2} °C → {3} %',
    'curve.delete': 'Удалить точку',
    'curve.reset': 'Стандартная кривая',
    'curve.save': 'Сохранить',
    'curve.cancel': 'Отмена',
    'curve.saved': 'Кривая сохранена',
    'curve.saveFail': 'Кривая отклонена: {0}',

    'init.title': 'Ошибка инициализации',
    'err.getConfig': 'Backend вернул неверный конфиг: {0}',
    'err.getStats': 'Backend не отвечает',
    'err.backend': 'Backend: {0}',
    'err.save': 'Backend не принял изменение',
    'err.params': 'Backend не принял настройки Auto TDP',
    'err.toggle': 'Не удалось переключить Auto TDP',
    'err.plugin': 'Не удалось переключить плагин',
    'err.lang': 'Не удалось сохранить язык',
  },
};

// Подстановка {0}, {1}, ...
export const format = (s: string, args: Array<string | number>): string =>
  s.replace(/\{(\d+)\}/g, (_, i) => (args[Number(i)] !== undefined ? String(args[Number(i)]) : ''));

/** Язык Steam для режима auto: LocalizationManager клиента, иначе язык браузера CEF. */
export const steamLang = (): Lang => {
  try {
    const w: any = typeof window !== 'undefined' ? window : {};
    const locales = w.LocalizationManager && w.LocalizationManager.m_rgLocalesToUse;
    const first = Array.isArray(locales) && locales.length ? String(locales[0]).toLowerCase() : '';
    if (first) return first.startsWith('russian') || first.startsWith('ru') ? 'ru' : 'en';
    const nav = typeof navigator !== 'undefined' ? String(navigator.language || '').toLowerCase() : '';
    return nav.startsWith('ru') ? 'ru' : 'en';
  } catch {
    return 'en';
  }
};

export const resolveLang = (lang: string | undefined): Lang =>
  lang === 'ru' ? 'ru' : lang === 'en' ? 'en' : steamLang();

export const translate = (lang: string | undefined, key: string, ...args: Array<string | number>): string => {
  const l = resolveLang(lang);
  const s = DICT[l][key] ?? DICT.en[key] ?? key;
  return format(s, args);
};
