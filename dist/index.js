var AutoTDP_Plugin = (function (React, ui) {
    'use strict';

    // SPDX-License-Identifier: MIT
    // Copyright (c) 2026 GPD5CachyAutoTDP Contributors
    // Словарь интерфейса (версия 2.2.0). Ключи должны совпадать для en и ru.
    const DICT = {
        en: {
            'section.autotdp': 'Auto TDP',
            'section.fps': 'Auto TDP / FPS',
            'section.status': 'Status',
            'section.fan': 'Fan curve',
            'section.source': 'FPS source / requirements',
            'toggle.autotdp': 'Auto TDP',
            'toggle.running': 'Running',
            'toggle.stopped': 'Stopped',
            'row.build': 'Build',
            'row.build.old': 'old backend: reinstall the archive',
            'row.tdpBackend': 'TDP backend',
            'row.currentTdp': 'Current TDP',
            'row.tdpSource': 'TDP source',
            'row.tdpSource.setpoint': 'setpoint (ryzenadj readback unavailable)',
            'row.avgFps': 'Average FPS',
            'row.effectiveGoal': 'Effective FPS goal',
            'row.tdpDecision': 'TDP decision',
            'row.tdpCapped': 'capped at {0} W',
            'row.minSearch': 'Minimum TDP search',
            'row.minSearch.value': '{0} W (probes: {1})',
            'fan.target': 'Fan target',
            'fan.applied': 'Fan applied',
            'fan.sensors': 'Temperature sensors',
            'row.cpuLoad': 'CPU load',
            'row.gpuLoad': 'GPU load',
            'row.controller': 'Controller',
            'row.controller.stopped': 'stopped',
            'slider.targetFps': 'Target FPS',
            'slider.startTdp': 'Start TDP',
            'slider.startTdp.on': 'Used when Auto TDP starts',
            'slider.startTdp.off': 'Applied when Auto TDP is switched off',
            'slider.minTdp': 'Minimum TDP',
            'slider.maxTdp': 'Maximum TDP',
            'slider.threshold': 'High-load threshold',
            'toggle.loadBoost': 'High-load TDP boost',
            'toggle.loadBoost.on': 'CPU >{0}% boosts TDP even when FPS is already on target; GPU >{0}% boosts only when FPS is below target',
            'toggle.loadBoost.off': 'Disabled',
            'fan.controller': 'Controller',
            'fan.controller.ok': 'gpdfan / PWM',
            'fan.controller.none': 'not detected',
            'fan.temp': 'Temperature',
            'fan.channels': 'Channels',
            'fan.rpm': 'Fan RPM',
            'fan.pwm': 'PWM',
            'fan.control': 'Fan control',
            'fan.control.on': 'Curve enabled',
            'fan.control.off': 'Curve disabled',
            'fan.notDetected': 'PWM fan controller not detected.',
            'src.note': 'Keep system MangoHud enabled. For correct AutoTDP behavior, disable FPS limits both in the game and in the system/gamescope. The plugin needs uncapped FPS to see the real performance headroom.',
            'src.source': 'Source',
            'src.sourceDefault': 'MangoHud / mangoapp CSV',
            'src.hud': 'MangoHud display',
            'src.hud.on': 'HUD visible',
            'src.hud.off': 'HUD hidden (logging remains active)',
            'search.title': 'TDP search',
            'search.state': 'Search state',
            'search.state.idle': 'not started',
            'search.state.probing': 'testing a level',
            'search.state.searching': 'narrowing the range',
            'search.state.done': 'minimum found',
            'search.good': 'Holds the goal at',
            'search.bad': 'Below the goal at',
            'search.probes': 'Tries',
            'search.unknown': '—',
            'init.title': 'Initialization errors',
            'curve.title': 'Fan curve editor',
            'curve.temp': 'Temp, °C',
            'curve.speed': 'Speed, %',
            'curve.point': 'Point {0}',
            'curve.add': 'Add point',
            'curve.remove': 'Remove last point',
            'curve.save': 'Save curve',
            'curve.reset': 'Reset to default',
            'curve.saved': 'Curve saved',
            'curve.saveFail': 'Curve rejected: {0}',
            'curve.hint': 'Temperatures 20–110 °C, speed 0–100 %. Speed must not fall as temperature rises.',
            'slider.interval': 'Poll interval',
            'slider.interval.desc': 'How often FPS is read and TDP may change. Shorter reacts faster but reads the log more often; 1 s is a good default.',
            'lang.title': 'Language',
            'lang.en': 'English',
            'lang.ru': 'Русский',
            'status.connecting': 'Connecting to backend…',
            'err.getConfig': 'Backend RPC get_config returned an invalid response: {0}',
            'err.getStats': 'Backend RPC get_stats does not respond',
            'err.backend': 'AutoTDP backend: {0}',
            'err.save': 'Backend did not accept the change',
            'err.params': 'Backend did not accept AutoTDP parameters',
            'err.toggle': 'Could not change AutoTDP state',
            'err.lang': 'Could not save the language',
        },
        ru: {
            'section.autotdp': 'Auto TDP',
            'section.fps': 'Auto TDP / FPS',
            'section.status': 'Статус',
            'section.fan': 'Кривая вентилятора',
            'section.source': 'Источник FPS / требования',
            'toggle.autotdp': 'Auto TDP',
            'toggle.running': 'Работает',
            'toggle.stopped': 'Остановлен',
            'row.build': 'Сборка',
            'row.build.old': 'старый backend: переустановите архив',
            'row.tdpBackend': 'Бэкенд TDP',
            'row.currentTdp': 'Текущий TDP',
            'row.tdpSource': 'Источник TDP',
            'row.tdpSource.setpoint': 'заданное значение (чтение ryzenadj недоступно)',
            'row.avgFps': 'Средний FPS',
            'row.effectiveGoal': 'Эффективная цель FPS',
            'row.tdpDecision': 'Решение по TDP',
            'row.tdpCapped': 'ограничено {0} Вт',
            'row.minSearch': 'Поиск минимума TDP',
            'row.minSearch.value': '{0} Вт (проб: {1})',
            'fan.target': 'Цель вентилятора',
            'fan.applied': 'Вентилятор сейчас',
            'fan.sensors': 'Датчики температуры',
            'row.cpuLoad': 'Загрузка CPU',
            'row.gpuLoad': 'Загрузка GPU',
            'row.controller': 'Контроллер',
            'row.controller.stopped': 'остановлен',
            'slider.targetFps': 'Целевой FPS',
            'slider.startTdp': 'Стартовый TDP',
            'slider.startTdp.on': 'Используется при запуске Auto TDP',
            'slider.startTdp.off': 'Применяется при выключении Auto TDP',
            'slider.minTdp': 'Минимальный TDP',
            'slider.maxTdp': 'Максимальный TDP',
            'slider.threshold': 'Порог высокой нагрузки',
            'toggle.loadBoost': 'Повышение TDP при высокой нагрузке',
            'toggle.loadBoost.on': 'CPU >{0}% повышает TDP даже когда FPS уже на цели; GPU >{0}% повышает только когда FPS ниже цели',
            'toggle.loadBoost.off': 'Выключено',
            'fan.controller': 'Контроллер',
            'fan.controller.ok': 'gpdfan / PWM',
            'fan.controller.none': 'не обнаружен',
            'fan.temp': 'Температура',
            'fan.channels': 'Каналы',
            'fan.rpm': 'Обороты вентилятора',
            'fan.pwm': 'PWM',
            'fan.control': 'Управление вентилятором',
            'fan.control.on': 'Кривая включена',
            'fan.control.off': 'Кривая выключена',
            'fan.notDetected': 'Контроллер PWM-вентилятора не обнаружен.',
            'src.note': 'Оставьте системный MangoHud включённым. Для корректной работы Auto TDP отключите ограничение FPS и в игре, и в системе/gamescope. Плагину нужен неограниченный FPS, чтобы видеть реальный запас производительности.',
            'src.source': 'Источник',
            'src.sourceDefault': 'MangoHud / CSV mangoapp',
            'src.hud': 'Отображение MangoHud',
            'src.hud.on': 'HUD виден',
            'src.hud.off': 'HUD скрыт (запись в лог продолжается)',
            'search.title': 'Поиск TDP',
            'search.state': 'Состояние поиска',
            'search.state.idle': 'не начат',
            'search.state.probing': 'проверка уровня',
            'search.state.searching': 'сужение отрезка',
            'search.state.done': 'минимум найден',
            'search.good': 'Держит цель на',
            'search.bad': 'Ниже цели на',
            'search.probes': 'Проб',
            'search.unknown': '—',
            'init.title': 'Ошибки инициализации',
            'curve.title': 'Редактор кривой вентилятора',
            'curve.temp': 'Температура, °C',
            'curve.speed': 'Скорость, %',
            'curve.point': 'Точка {0}',
            'curve.add': 'Добавить точку',
            'curve.remove': 'Удалить последнюю точку',
            'curve.save': 'Сохранить кривую',
            'curve.reset': 'Сбросить к стандартной',
            'curve.saved': 'Кривая сохранена',
            'curve.saveFail': 'Кривая отклонена: {0}',
            'curve.hint': 'Температура 20–110 °C, скорость 0–100 %. Скорость не должна падать с ростом температуры.',
            'slider.interval': 'Интервал опроса',
            'slider.interval.desc': 'Как часто читается FPS и может меняться TDP. Меньше — быстрее реакция, но чаще чтение лога; 1 с — разумный выбор.',
            'lang.title': 'Язык',
            'lang.en': 'English',
            'lang.ru': 'Русский',
            'status.connecting': 'Подключение к backend…',
            'err.getConfig': 'Backend RPC get_config вернул неверный ответ: {0}',
            'err.getStats': 'Backend RPC get_stats не отвечает',
            'err.backend': 'AutoTDP backend: {0}',
            'err.save': 'Backend не принял изменение',
            'err.params': 'Backend не принял параметры AutoTDP',
            'err.toggle': 'Не удалось изменить состояние AutoTDP',
            'err.lang': 'Не удалось сохранить язык',
        },
    };
    // Подстановка {0}, {1}, ...
    const format = (s, args) => s.replace(/\{(\d+)\}/g, (_, i) => (args[Number(i)] !== undefined ? String(args[Number(i)]) : ''));
    const translate = (lang, key, ...args) => {
        const l = lang === 'ru' ? 'ru' : 'en';
        const s = DICT[l][key] ?? DICT.en[key] ?? key;
        return format(s, args);
    };

    // SPDX-License-Identifier: MIT
    // Copyright (c) 2026 GPD5CachyAutoTDP Contributors
    const DEFAULT_CONFIG = {
        enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 80, initial_tdp: 35, load_boost_enabled: true, load_boost_threshold: 95, mangohud_display: false, language: 'en',
        check_interval_sec: 3, hysteresis_threshold: 5,
        fan_control: { enabled: true },
    };
    const LOOKS_LIKE_CONFIG = ['enabled', 'target_fps', 'min_tdp', 'max_tdp', 'initial_tdp', 'fan_control'];
    const looksLikeConfig = (o) => LOOKS_LIKE_CONFIG.filter(k => Object.prototype.hasOwnProperty.call(o, k)).length >= 2;
    // Разворачивает legacy-конверт Decky {result, success}. Строку ошибки бэкенда
    // (success:false) не принимаем за данные — возвращаем {__error}.
    const unwrap = (v) => {
        let value = v;
        for (let depth = 0; depth < 4; depth++) {
            if (typeof value === 'string') {
                try {
                    value = JSON.parse(value);
                    continue;
                }
                catch {
                    return value;
                }
            }
            if (!value || typeof value !== 'object' || Array.isArray(value))
                return value;
            if (value.success === false) {
                return { __error: typeof value.result === 'string' ? value.result : JSON.stringify(value.result) };
            }
            if (looksLikeConfig(value))
                return value;
            if (Object.prototype.hasOwnProperty.call(value, 'result')) {
                value = value.result;
                continue;
            }
            if (Object.prototype.hasOwnProperty.call(value, 'data')) {
                value = value.data;
                continue;
            }
            return value;
        }
        return value;
    };
    const describe = (v) => v === undefined ? 'undefined' : v === null ? 'null' : typeof v === 'string' ? v : JSON.stringify(v);
    const safeNum = (v, fallback) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : fallback;
    };
    const Row = ({ label, value }) => (React.createElement(ui.PanelSectionRow, null,
        React.createElement("div", { style: { display: 'flex', justifyContent: 'space-between', width: '100%', gap: 12 } },
            React.createElement("span", null, label),
            React.createElement("span", { style: { fontFamily: 'monospace' } }, value == null ? '—' : String(value)))));
    function makeContent(serverAPI) {
        const rpc = async (method, args = {}) => {
            try {
                const raw = await serverAPI.callPluginMethod(method, args);
                const result = unwrap(raw);
                console.log('[AutoTDP] RPC', method, result);
                return result;
            }
            catch (e) {
                console.error('[AutoTDP] RPC', method, e);
                return null;
            }
        };
        return function Content() {
            const [cfg, setCfg] = React.useState(null);
            const [stats, setStats] = React.useState(null);
            const [error, setError] = React.useState('');
            const [curveEdit, setCurveEdit] = React.useState(null);
            const [curveMsg, setCurveMsg] = React.useState('');
            const tr = (key, ...args) => translate(cfg && cfg.language, key, ...args);
            const pendingTimers = React.useRef({});
            const refreshBlockedUntil = React.useRef(0);
            const refresh = async () => {
                if (Date.now() < refreshBlockedUntil.current)
                    return;
                const c = await rpc('get_config');
                if (c && c.__error) {
                    setError(tr('err.getConfig', c.__error));
                    return;
                }
                if (c && typeof c === 'object' && !Array.isArray(c)) {
                    setError(c._backend_error ? tr('err.backend', c._backend_error) : '');
                    setCfg({ ...DEFAULT_CONFIG, ...c, fan_control: { ...DEFAULT_CONFIG.fan_control, ...(c.fan_control || {}) } });
                }
                else {
                    setError(tr('err.getConfig', describe(c)));
                    return;
                }
                const s = await rpc('get_stats');
                if (s && typeof s === 'object')
                    setStats(s);
                else
                    setError(tr('err.getStats'));
            };
            React.useEffect(() => {
                refresh();
                const timer = setInterval(refresh, 2000);
                return () => clearInterval(timer);
            }, []);
            if (!cfg)
                return React.createElement(ui.PanelSection, { title: tr('section.fps') },
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement("span", null, error || tr('status.connecting'))));
            const save = async (key, value) => {
                setCfg((x) => ({ ...x, [key]: value }));
                const ok = await rpc('set_config_value', { key, value });
                if (!ok)
                    setError(tr('err.save'));
                return ok;
            };
            const updateMonitorParam = (key, value) => {
                setCfg((x) => ({ ...x, [key]: value }));
                const oldTimer = pendingTimers.current[key];
                if (oldTimer)
                    clearTimeout(oldTimer);
                refreshBlockedUntil.current = Date.now() + 700;
                pendingTimers.current[key] = setTimeout(async () => {
                    const args = {};
                    if (key === 'min_tdp')
                        args.min_tdp = safeNum(value, 15);
                    else if (key === 'max_tdp')
                        args.max_tdp = safeNum(value, 80);
                    else if (key === 'target_fps')
                        args.target_fps = safeNum(value, 40);
                    else {
                        await save(key, value);
                        return;
                    }
                    const ok = await rpc('update_monitor_params', args);
                    if (!ok)
                        setError(tr('err.params'));
                    refreshBlockedUntil.current = Date.now() + 500;
                }, 250);
            };
            const enabled = !!cfg.enabled;
            const toggle = async (value) => {
                const ok = value
                    ? await rpc('start_monitor', { min_tdp: safeNum(cfg.min_tdp, 15), max_tdp: safeNum(cfg.max_tdp, 80), target_fps: safeNum(cfg.target_fps, 40), enable_auto: true })
                    : await rpc('stop_monitor');
                if (!ok) {
                    setError(tr('err.toggle'));
                    return;
                }
                await save('enabled', value);
                await refresh();
            };
            const t = (stats && stats.tdp) || {};
            const m = (stats && stats.monitor) || {};
            const f = (stats && stats.fan) || {};
            const curveFromConfig = (c) => {
                const cur = (c && c.fan_control && c.fan_control.curve) || {};
                const byTemp = {};
                Object.keys(cur).forEach((k) => {
                    const t = Number(k), s = Number(cur[k]);
                    if (!Number.isFinite(t) || !Number.isFinite(s))
                        return;
                    // Если в конфиге по одной температуре оказалось несколько значений (старый формат,
                    // ручная правка), оставляем МАКСИМУМ: выше скорость — безопаснее, и это убирает
                    // визуальные «дубли» точек.
                    byTemp[t] = byTemp[t] === undefined ? Math.max(0, Math.min(100, s)) : Math.max(byTemp[t], Math.max(0, Math.min(100, s)));
                });
                const arr = Object.keys(byTemp).map((k) => ({ t: Number(k), s: byTemp[Number(k)] }));
                arr.sort((a, b) => a.t - b.t);
                return arr.length ? arr : [{ t: 50, s: 20 }, { t: 95, s: 100 }];
            };
            const updateCurvePoint = (list, i, key, v) => list.map((p, j) => j === i ? { ...p, [key]: v } : p);
            const target = safeNum(cfg.target_fps, 40);
            const minTdp = safeNum(cfg.min_tdp, 15);
            const maxTdp = Math.min(80, safeNum(cfg.max_tdp, 80));
            const initialTdp = safeNum(cfg.initial_tdp, 35);
            return React.createElement(React.Fragment, null,
                React.createElement(ui.PanelSection, { title: tr('section.autotdp') },
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('toggle.autotdp'), description: enabled ? tr('toggle.running') : tr('toggle.stopped'), checked: enabled, onChange: toggle }))),
                (error || (stats && stats.init_errors && stats.init_errors.length)) && React.createElement(ui.PanelSection, { title: tr('section.status') },
                    error && React.createElement(ui.PanelSectionRow, null,
                        React.createElement("span", { style: { color: '#ffb3b3' } }, error)),
                    stats && stats.init_errors && stats.init_errors.map((e, i) => React.createElement(ui.PanelSectionRow, { key: i },
                        React.createElement("span", { style: { color: '#ffb3b3' } },
                            tr('init.title'),
                            ": ",
                            String(e))))),
                React.createElement(ui.PanelSection, { title: tr('section.fps') },
                    React.createElement(Row, { label: tr('row.build'), value: (stats && stats.build) || tr('row.build.old') }),
                    React.createElement(Row, { label: tr('row.tdpBackend'), value: t.backend || 'none' }),
                    React.createElement(Row, { label: tr('row.currentTdp'), value: t.current_tdp != null ? `${safeNum(t.current_tdp, 0).toFixed(1)} W` : '—' }),
                    React.createElement(Row, { label: tr('row.tdpSource'), value: t.tdp_source === 'setpoint' ? tr('row.tdpSource.setpoint') : (t.tdp_source || '—') }),
                    React.createElement(Row, { label: tr('row.avgFps'), value: m.last_fps != null ? safeNum(m.last_fps, 0).toFixed(1) : '—' }),
                    React.createElement(Row, { label: tr('row.effectiveGoal'), value: m.effective_target_fps != null ? String(m.effective_target_fps) : '—' }),
                    React.createElement(Row, { label: tr('row.tdpDecision'), value: m.tdp_hold_level != null ? tr('row.tdpCapped', m.tdp_hold_level) : (m.tdp_decision || '—') }),
                    React.createElement(Row, { label: tr('search.state'), value: tr('search.state.' + ((m.tdp_search && m.tdp_search.state) || 'idle')) }),
                    React.createElement(Row, { label: tr('search.good'), value: (m.tdp_search && m.tdp_search.good_w) != null ? `${m.tdp_search.good_w} W` : tr('search.unknown') }),
                    React.createElement(Row, { label: tr('search.bad'), value: (m.tdp_search && m.tdp_search.bad_w) != null ? `${m.tdp_search.bad_w} W` : tr('search.unknown') }),
                    React.createElement(Row, { label: tr('search.probes'), value: (m.tdp_search && (m.tdp_search.last_search_probes || m.tdp_search.probes)) || 0 }),
                    React.createElement(Row, { label: tr('row.cpuLoad'), value: m.last_cpu_load != null ? `${safeNum(m.last_cpu_load, 0).toFixed(1)}%` : '—' }),
                    React.createElement(Row, { label: tr('row.gpuLoad'), value: m.last_gpu_load != null ? `${safeNum(m.last_gpu_load, 0).toFixed(1)}%` : '—' }),
                    React.createElement(Row, { label: tr('row.controller'), value: m.state || tr('row.controller.stopped') }),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.targetFps'), value: target, min: 30, max: 120, step: 5, showValue: true, onChange: (v) => updateMonitorParam('target_fps', v) })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.startTdp'), description: enabled ? tr('slider.startTdp.on') : tr('slider.startTdp.off'), value: initialTdp, min: 5, max: 80, step: 1, showValue: true, valueSuffix: " W", onChange: async (v) => { const ok = await save('initial_tdp', v); if (ok && !enabled)
                                await rpc('set_tdp', { value: v }); } })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.minTdp'), value: minTdp, min: 5, max: maxTdp, step: 1, showValue: true, valueSuffix: " W", onChange: (v) => updateMonitorParam('min_tdp', v) })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.maxTdp'), value: maxTdp, min: minTdp, max: 80, step: 1, showValue: true, valueSuffix: " W", onChange: (v) => updateMonitorParam('max_tdp', v) })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('toggle.loadBoost'), description: cfg.load_boost_enabled ? tr('toggle.loadBoost.on', safeNum(cfg.load_boost_threshold, 95)) : tr('toggle.loadBoost.off'), checked: !!cfg.load_boost_enabled, onChange: async (v) => { const ok = await save('load_boost_enabled', v); if (ok)
                                await refresh(); } })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.interval'), description: tr('slider.interval.desc'), value: safeNum(cfg.check_interval_sec, 1), min: 0.5, max: 5, step: 0.5, showValue: true, valueSuffix: " s", onChange: async (v) => { setCfg((x) => ({ ...x, check_interval_sec: v })); const ok = await rpc('set_check_interval', { seconds: v }); if (!ok)
                                setError(tr('err.save')); } })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.SliderField, { label: tr('slider.threshold'), value: safeNum(cfg.load_boost_threshold, 95), min: 90, max: 100, step: 1, showValue: true, valueSuffix: "%", onChange: (v) => save('load_boost_threshold', v) }))),
                React.createElement(ui.PanelSection, { title: tr('section.fan') },
                    React.createElement(Row, { label: tr('fan.controller'), value: f.available ? tr('fan.controller.ok') : tr('fan.controller.none') }),
                    React.createElement(Row, { label: tr('fan.temp'), value: f.current_temperature != null ? `${safeNum(f.current_temperature, 0).toFixed(1)} °C` : '—' }),
                    React.createElement(Row, { label: tr('fan.channels'), value: f.channels || 0 }),
                    React.createElement(Row, { label: tr('fan.rpm'), value: f.fan_rpm?.length ? f.fan_rpm.map((v) => v == null ? '—' : v).join(', ') : '—' }),
                    React.createElement(Row, { label: tr('fan.pwm'), value: f.pwm_percent?.length ? f.pwm_percent.map((v) => v == null ? '—' : `${v.toFixed(1)}%`).join(', ') : '—' }),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('fan.control'), description: cfg.fan_control?.enabled ? tr('fan.control.on') : tr('fan.control.off'), checked: !!cfg.fan_control?.enabled, disabled: !f.available, onChange: async (v) => { const ok = await rpc(v ? 'enable_fan_control' : 'disable_fan_control'); if (ok)
                                await refresh(); } })),
                    !f.available && React.createElement(ui.PanelSectionRow, null,
                        React.createElement("span", { style: { color: '#94a3b8' } }, tr('fan.notDetected'))),
                    f.available && React.createElement(React.Fragment, null,
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement("span", { style: { color: '#dbeafe' } }, tr('curve.hint'))),
                        (curveEdit || curveFromConfig(cfg)).map((pt, i) => (React.createElement(ui.PanelSectionRow, { key: `t${i}` },
                            React.createElement(ui.SliderField, { label: `${tr('curve.point', i + 1)} — ${tr('curve.temp')}`, value: pt.t, min: 20, max: 110, step: 1, showValue: true, onChange: (v) => setCurveEdit(updateCurvePoint(curveEdit || curveFromConfig(cfg), i, 't', v)) })))),
                        (curveEdit || curveFromConfig(cfg)).map((pt, i) => (React.createElement(ui.PanelSectionRow, { key: `s${i}` },
                            React.createElement(ui.SliderField, { label: `${tr('curve.point', i + 1)} — ${tr('curve.speed')}`, value: pt.s, min: 0, max: 100, step: 1, showValue: true, onChange: (v) => setCurveEdit(updateCurvePoint(curveEdit || curveFromConfig(cfg), i, 's', v)) })))),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(ui.ButtonItem, { onClick: () => setCurveEdit([...(curveEdit || curveFromConfig(cfg)), { t: 100, s: 100 }]) }, tr('curve.add'))),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(ui.ButtonItem, { onClick: () => setCurveEdit((curveEdit || curveFromConfig(cfg)).slice(0, -1)) }, tr('curve.remove'))),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(ui.ButtonItem, { onClick: async () => {
                                    const list = curveEdit || curveFromConfig(cfg);
                                    // Склеиваем точки с одинаковой температурой, оставляя бо́льшую скорость:
                                    // иначе бэкенд получит словарь с потерянными точками, а редактор покажет их заново.
                                    const obj = {};
                                    list.forEach((p) => {
                                        const key = String(Math.round(p.t)), val = Math.round(p.s);
                                        obj[key] = obj[key] === undefined ? val : Math.max(obj[key], val);
                                    });
                                    const res = await rpc('set_fan_curve', { curve: obj });
                                    if (res && res.ok) {
                                        setCurveMsg(tr('curve.saved'));
                                        setCurveEdit(null);
                                        await refresh();
                                    }
                                    else
                                        setCurveMsg(tr('curve.saveFail', (res && res.error) || tr('search.unknown')));
                                } }, tr('curve.save'))),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(ui.ButtonItem, { onClick: async () => { const res = await rpc('reset_fan_curve'); if (res && res.ok) {
                                    setCurveEdit(null);
                                    setCurveMsg('');
                                    await refresh();
                                }
                                else
                                    setCurveMsg(tr('curve.saveFail', (res && res.error) || tr('search.unknown'))); } }, tr('curve.reset'))),
                        curveMsg && React.createElement(ui.PanelSectionRow, null,
                            React.createElement("span", { style: { color: '#dbeafe' } }, curveMsg)))),
                React.createElement(ui.PanelSection, { title: tr('section.source') },
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement("span", { style: { color: '#dbeafe' } }, tr('src.note'))),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(Row, { label: tr('src.source'), value: m.fps_source || tr('src.sourceDefault') })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('src.hud'), description: cfg.mangohud_display ? tr('src.hud.on') : tr('src.hud.off'), checked: !!cfg.mangohud_display, onChange: async (v) => { const ok = await rpc('set_mangohud_display', { enabled: v }); if (ok)
                                await refresh(); } }))),
                React.createElement(ui.PanelSection, { title: tr('lang.title') },
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('lang.en'), description: cfg.language === 'en' ? '✓' : '', checked: cfg.language === 'en', onChange: async (v) => { if (!v)
                                return; const ok = await rpc('set_language', { language: 'en' }); if (ok)
                                await refresh();
                            else
                                setError(tr('err.lang')); } })),
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('lang.ru'), description: cfg.language === 'ru' ? '✓' : '', checked: cfg.language === 'ru', onChange: async (v) => { if (!v)
                                return; const ok = await rpc('set_language', { language: 'ru' }); if (ok)
                                await refresh();
                            else
                                setError(tr('err.lang')); } }))));
        };
    }
    function createPlugin(serverAPI) {
        const Content = makeContent(serverAPI);
        return {
            title: React.createElement("div", { className: ui.staticClasses?.Title || '' }, "GPD5CachyAutoTDP"),
            content: React.createElement(Content, null),
            icon: React.createElement("span", null, "\u26A1"),
            onDismount() { }
        };
    }

    return createPlugin;

})(SP_REACT, DFL);
AutoTDP_Plugin
