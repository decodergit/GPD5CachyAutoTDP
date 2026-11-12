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
            'section.plugin': 'Plugin',
            'toggle.plugin': 'Plugin enabled',
            'toggle.plugin.on': 'Controls TDP and fan',
            'toggle.plugin.off': 'Fully off: TDP and fan are not touched',
            'toggle.plugin.gui': 'Paused: the tdp_gui.py window is open (pid {0})',
            'err.plugin': 'Could not switch the plugin',
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
            'row.game': 'Game',
            'row.game.unknown': 'not detected (shared stats)',
            'row.levels': 'Working TDP levels',
            'row.levels.none': 'not learned yet',
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
            'curve.edit': 'Edit curve',
            'curve.graphHint': 'Drag a point to move it, tap empty space to add one. Speed cannot fall as temperature rises.',
            'curve.prev': '◀ Point',
            'curve.next': 'Point ▶',
            'curve.selected': 'Point {0} of {1}: {2} °C → {3} %',
            'curve.delete': 'Delete point',
            'curve.cancel': 'Cancel',
            'curve.now': 'now {0} °C · {1} %',
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
            'section.plugin': 'Плагин',
            'toggle.plugin': 'Плагин включён',
            'toggle.plugin.on': 'Управляет TDP и вентилятором',
            'toggle.plugin.off': 'Полностью отключён: TDP и вентилятор не трогаются',
            'toggle.plugin.gui': 'Приостановлен: открыто окно tdp_gui.py (pid {0})',
            'err.plugin': 'Не удалось переключить плагин',
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
            'row.game': 'Игра',
            'row.game.unknown': 'не определена (общая статистика)',
            'row.levels': 'Рабочие уровни TDP',
            'row.levels.none': 'пока не накоплены',
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
            'curve.edit': 'Изменить кривую',
            'curve.graphHint': 'Перетащите точку, чтобы сдвинуть её; коснитесь пустого места, чтобы добавить. Скорость не может падать с ростом температуры.',
            'curve.prev': '◀ Точка',
            'curve.next': 'Точка ▶',
            'curve.selected': 'Точка {0} из {1}: {2} °C → {3} %',
            'curve.delete': 'Удалить точку',
            'curve.cancel': 'Отмена',
            'curve.now': 'сейчас {0} °C · {1} %',
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
    //
    // Кривая вентилятора в виде графика (3.5.0): компактный график в панели и редактор
    // в модальном окне. Точки перетаскиваются пальцем, касание пустого места добавляет точку;
    // для геймпада есть переключение точек и ползунки выбранной точки.
    // Границы совпадают с FanController.validate_curve.
    const T_MIN = 20, T_MAX = 110, S_MIN = 0, S_MAX = 100;
    // Совпадает с FanController.DEFAULT_CURVE.
    const DEFAULT_CURVE = [
        { t: 50, s: 20 }, { t: 60, s: 25 }, { t: 65, s: 30 }, { t: 70, s: 35 }, { t: 75, s: 42 },
        { t: 80, s: 55 }, { t: 85, s: 70 }, { t: 90, s: 85 }, { t: 95, s: 100 },
    ];
    const ACCENT = '#1a9fff';
    const NOW = '#ffb347';
    const GRID = 'rgba(255,255,255,0.08)';
    const LABEL = '#8b929a';
    // --- геометрия --------------------------------------------------------------
    const VB_W = 400;
    const PAD = { l: 30, r: 16, t: 8, b: 20 };
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    function geometry(height) {
        const pw = VB_W - PAD.l - PAD.r;
        const ph = height - PAD.t - PAD.b;
        return {
            pw, ph,
            x: (t) => PAD.l + (t - T_MIN) / (T_MAX - T_MIN) * pw,
            y: (s) => PAD.t + (1 - (s - S_MIN) / (S_MAX - S_MIN)) * ph,
            t: (px) => T_MIN + (px - PAD.l) / pw * (T_MAX - T_MIN),
            s: (py) => S_MIN + (1 - (py - PAD.t) / ph) * (S_MAX - S_MIN),
        };
    }
    // --- данные -------------------------------------------------------------------
    /** Сортирует, склеивает одинаковые температуры (берёт бо́льшую скорость), делает кривую неубывающей. */
    function normalizeCurve(pts) {
        const byT = {};
        pts.forEach(p => {
            const t = Math.round(clamp(Number(p.t), T_MIN, T_MAX));
            const s = Math.round(clamp(Number(p.s), S_MIN, S_MAX));
            if (!Number.isFinite(t) || !Number.isFinite(s))
                return;
            byT[t] = byT[t] === undefined ? s : Math.max(byT[t], s);
        });
        const out = Object.keys(byT).map(k => ({ t: Number(k), s: byT[Number(k)] })).sort((a, b) => a.t - b.t);
        for (let i = 1; i < out.length; i++)
            out[i].s = Math.max(out[i].s, out[i - 1].s);
        return out;
    }
    /** Скорость по кривой при температуре t (как FanController.calc). */
    function curveAt(pts, t) {
        if (!pts.length)
            return S_MAX;
        if (t <= pts[0].t)
            return pts[0].s;
        if (t >= pts[pts.length - 1].t)
            return pts[pts.length - 1].s;
        for (let i = 1; i < pts.length; i++) {
            const a = pts[i - 1], b = pts[i];
            if (t <= b.t)
                return a.s + (t - a.t) * (b.s - a.s) / (b.t - a.t);
        }
        return pts[pts.length - 1].s;
    }
    /** Ставит точку i в (t, s): температура между соседями, скорость «толкает» соседей,
     *  чтобы кривая оставалась неубывающей. */
    function movePoint(pts, i, t, s) {
        const out = pts.map(p => ({ ...p }));
        const lo = i > 0 ? out[i - 1].t + 1 : T_MIN;
        const hi = i < out.length - 1 ? out[i + 1].t - 1 : T_MAX;
        out[i].t = Math.round(clamp(t, lo, hi));
        out[i].s = Math.round(clamp(s, S_MIN, S_MAX));
        for (let j = i + 1; j < out.length; j++)
            out[j].s = Math.max(out[j].s, out[i].s);
        for (let j = i - 1; j >= 0; j--)
            out[j].s = Math.min(out[j].s, out[i].s);
        return out;
    }
    function addPoint(pts, t, s) {
        const tt = Math.round(clamp(t, T_MIN, T_MAX));
        if (pts.some(p => p.t === tt))
            return null;
        const out = [...pts.map(p => ({ ...p })), { t: tt, s: 0 }].sort((a, b) => a.t - b.t);
        const index = out.findIndex(p => p.t === tt);
        return { pts: movePoint(out, index, tt, s), index };
    }
    function CurveGraph({ points, now, height, selected = null, svgRef, handlers }) {
        const g = geometry(height);
        const pts = points.length ? points : [{ t: T_MIN, s: S_MAX }];
        const line = [
            [g.x(T_MIN), g.y(pts[0].s)],
            ...pts.map(p => [g.x(p.t), g.y(p.s)]),
            [g.x(T_MAX), g.y(pts[pts.length - 1].s)],
        ];
        const lineStr = line.map(([a, b]) => `${a.toFixed(1)},${b.toFixed(1)}`).join(' ');
        const area = `${g.x(T_MIN)},${g.y(0)} ${lineStr} ${g.x(T_MAX)},${g.y(0)}`;
        const tTicks = [30, 50, 70, 90, 110];
        const sTicks = [0, 25, 50, 75, 100];
        const nowT = now && now.t != null ? clamp(now.t, T_MIN, T_MAX) : null;
        const nowS = nowT == null ? null : (now && now.s != null ? clamp(now.s, S_MIN, S_MAX) : curveAt(pts, nowT));
        const r = height > 160 ? 6 : 3.5;
        return (React.createElement("svg", { ref: svgRef, viewBox: `0 0 ${VB_W} ${height}`, width: "100%", style: { display: 'block', touchAction: 'none', userSelect: 'none' }, ...handlers },
            React.createElement("rect", { x: PAD.l, y: PAD.t, width: g.pw, height: g.ph, fill: "rgba(0,0,0,0.25)", rx: 3 }),
            [20, 40, 60, 80, 100].map(t => React.createElement("line", { key: `gt${t}`, x1: g.x(t + 10), x2: g.x(t + 10), y1: PAD.t, y2: PAD.t + g.ph, stroke: GRID })),
            sTicks.map(s => React.createElement("line", { key: `gs${s}`, x1: PAD.l, x2: PAD.l + g.pw, y1: g.y(s), y2: g.y(s), stroke: GRID })),
            tTicks.map(t => React.createElement("text", { key: `lt${t}`, x: g.x(t), y: height - 5, fill: LABEL, fontSize: 11, textAnchor: "middle" },
                t,
                "\u00B0")),
            sTicks.map(s => React.createElement("text", { key: `ls${s}`, x: PAD.l - 4, y: g.y(s) + 4, fill: LABEL, fontSize: 11, textAnchor: "end" },
                s,
                "%")),
            React.createElement("polygon", { points: area, fill: "rgba(26,159,255,0.16)" }),
            React.createElement("polyline", { points: lineStr, fill: "none", stroke: ACCENT, strokeWidth: 2.5, strokeLinejoin: "round" }),
            nowT != null && React.createElement(React.Fragment, null,
                React.createElement("line", { x1: g.x(nowT), x2: g.x(nowT), y1: PAD.t, y2: PAD.t + g.ph, stroke: NOW, strokeWidth: 1.5, strokeDasharray: "4 3" }),
                React.createElement("circle", { cx: g.x(nowT), cy: g.y(nowS), r: r + 1, fill: NOW })),
            points.map((p, i) => (React.createElement("circle", { key: i, cx: g.x(p.t), cy: g.y(p.s), r: i === selected ? r + 3 : r, fill: i === selected ? '#ffffff' : ACCENT, stroke: i === selected ? ACCENT : '#0e141b', strokeWidth: 2 })))));
    }
    const EDITOR_H = 250;
    const HIT_RADIUS = 18; // в единицах viewBox: пальцу нужна зона больше самой точки
    function FanCurveModal({ initial, now, tr, closeModal, onSave }) {
        const [points, setPoints] = React.useState(() => {
            const n = normalizeCurve(initial);
            return n.length >= 2 ? n : DEFAULT_CURVE.map(p => ({ ...p }));
        });
        const [sel, setSel] = React.useState(0);
        const [msg, setMsg] = React.useState('');
        const [busy, setBusy] = React.useState(false);
        const svgRef = React.useRef(null);
        const drag = React.useRef(null);
        const g = geometry(EDITOR_H);
        const toView = (e) => {
            const rect = svgRef.current.getBoundingClientRect();
            return {
                px: (e.clientX - rect.left) / rect.width * VB_W,
                py: (e.clientY - rect.top) / rect.height * EDITOR_H,
            };
        };
        const onPointerDown = (e) => {
            const { px, py } = toView(e);
            let best = -1, bestD = HIT_RADIUS;
            points.forEach((p, i) => {
                const d = Math.hypot(g.x(p.t) - px, g.y(p.s) - py);
                if (d < bestD) {
                    best = i;
                    bestD = d;
                }
            });
            if (best < 0) {
                const added = addPoint(points, g.t(px), g.s(py));
                if (!added)
                    return;
                setPoints(added.pts);
                best = added.index;
            }
            setSel(best);
            drag.current = best;
            setMsg('');
            try {
                e.currentTarget.setPointerCapture(e.pointerId);
            }
            catch { /* старый CEF */ }
        };
        const onPointerMove = (e) => {
            if (drag.current == null)
                return;
            const { px, py } = toView(e);
            const i = drag.current;
            setPoints(prev => movePoint(prev, i, g.t(px), g.s(py)));
        };
        const endDrag = () => { drag.current = null; };
        const cur = points[Math.min(sel, points.length - 1)];
        const idx = Math.min(sel, points.length - 1);
        const tLo = idx > 0 ? points[idx - 1].t + 1 : T_MIN;
        const tHi = idx < points.length - 1 ? points[idx + 1].t - 1 : T_MAX;
        const save = async () => {
            setBusy(true);
            const res = await onSave(normalizeCurve(points));
            setBusy(false);
            if (res && res.ok) {
                closeModal && closeModal();
                return;
            }
            setMsg(tr('curve.saveFail', (res && res.error) || '?'));
        };
        return (React.createElement(ui.ModalRoot, { closeModal: closeModal, onCancel: closeModal },
            React.createElement("div", { style: { fontSize: 18, fontWeight: 'bold', marginBottom: 6 } }, tr('curve.title')),
            React.createElement(CurveGraph, { points: points, now: now, height: EDITOR_H, selected: idx, svgRef: svgRef, handlers: { onPointerDown, onPointerMove, onPointerUp: endDrag, onPointerCancel: endDrag, onPointerLeave: endDrag } }),
            React.createElement("div", { style: { fontSize: 12, color: LABEL, margin: '4px 0 8px' } }, tr('curve.graphHint')),
            React.createElement(ui.Focusable, { style: { display: 'flex', gap: 8, alignItems: 'center' }, "flow-children": "horizontal" },
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, disabled: idx <= 0, onClick: () => setSel(idx - 1) }, tr('curve.prev')),
                React.createElement("div", { style: { flex: 2, textAlign: 'center', fontSize: 14 } }, tr('curve.selected', idx + 1, points.length, cur.t, cur.s)),
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, disabled: idx >= points.length - 1, onClick: () => setSel(idx + 1) }, tr('curve.next'))),
            React.createElement(ui.SliderField, { label: tr('curve.temp'), value: cur.t, min: tLo, max: Math.max(tLo, tHi), step: 1, showValue: true, onChange: (v) => setPoints(prev => movePoint(prev, idx, v, prev[idx].s)) }),
            React.createElement(ui.SliderField, { label: tr('curve.speed'), value: cur.s, min: S_MIN, max: S_MAX, step: 1, showValue: true, onChange: (v) => setPoints(prev => movePoint(prev, idx, prev[idx].t, v)) }),
            React.createElement(ui.Focusable, { style: { display: 'flex', gap: 8, marginTop: 10 }, "flow-children": "horizontal" },
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, disabled: points.length <= 2, onClick: () => { setPoints(points.filter((_, i) => i !== idx)); setSel(Math.max(0, idx - 1)); } }, tr('curve.delete')),
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, onClick: () => { setPoints(DEFAULT_CURVE.map(p => ({ ...p }))); setSel(0); setMsg(''); } }, tr('curve.reset'))),
            React.createElement(ui.Focusable, { style: { display: 'flex', gap: 8, marginTop: 8 }, "flow-children": "horizontal" },
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, disabled: busy, onClick: save }, tr('curve.save')),
                React.createElement(ui.DialogButton, { style: { minWidth: 0, flex: 1 }, onClick: () => closeModal && closeModal() }, tr('curve.cancel'))),
            msg && React.createElement("div", { style: { color: '#ffb3b3', marginTop: 8 } }, msg)));
    }

    // SPDX-License-Identifier: MIT
    // Copyright (c) 2026 GPD5CachyAutoTDP Contributors
    const DEFAULT_CONFIG = {
        plugin_enabled: true, enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 80, initial_tdp: 35, load_boost_enabled: true, load_boost_threshold: 95, mangohud_display: false, language: 'en',
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
            const pluginEnabled = cfg.plugin_enabled !== false;
            // active приходит из get_stats: false, если плагин выключен или приостановлен окном tdp_gui.py.
            const pluginActive = stats ? stats.active !== false : pluginEnabled;
            const guiPid = stats && stats.gui_pid;
            const togglePlugin = async (value) => {
                setCfg((x) => ({ ...x, plugin_enabled: value }));
                const ok = await rpc('set_plugin_enabled', { enabled: value });
                if (!ok)
                    setError(tr('err.plugin'));
                await refresh();
            };
            const pluginDesc = !pluginEnabled ? tr('toggle.plugin.off')
                : guiPid ? tr('toggle.plugin.gui', guiPid)
                    : tr('toggle.plugin.on');
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
            const target = safeNum(cfg.target_fps, 40);
            const minTdp = safeNum(cfg.min_tdp, 15);
            const maxTdp = Math.min(80, safeNum(cfg.max_tdp, 80));
            const initialTdp = safeNum(cfg.initial_tdp, 35);
            return React.createElement(React.Fragment, null,
                React.createElement(ui.PanelSection, { title: tr('section.plugin') },
                    React.createElement(ui.PanelSectionRow, null,
                        React.createElement(ui.ToggleField, { label: tr('toggle.plugin'), description: pluginDesc, checked: pluginEnabled, onChange: togglePlugin }))),
                pluginActive && React.createElement(ui.PanelSection, { title: tr('section.autotdp') },
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
                pluginActive && React.createElement(React.Fragment, null,
                    React.createElement(ui.PanelSection, { title: tr('section.fps') },
                        React.createElement(Row, { label: tr('row.build'), value: (stats && stats.build) || tr('row.build.old') }),
                        React.createElement(Row, { label: tr('row.tdpBackend'), value: t.backend || 'none' }),
                        React.createElement(Row, { label: tr('row.currentTdp'), value: t.current_tdp != null ? `${safeNum(t.current_tdp, 0).toFixed(1)} W` : '—' }),
                        React.createElement(Row, { label: tr('row.tdpSource'), value: t.tdp_source === 'setpoint' ? tr('row.tdpSource.setpoint') : (t.tdp_source || '—') }),
                        React.createElement(Row, { label: tr('row.avgFps'), value: m.last_fps != null ? safeNum(m.last_fps, 0).toFixed(1) : '—' }),
                        React.createElement(Row, { label: tr('row.effectiveGoal'), value: m.effective_target_fps != null ? String(m.effective_target_fps) : '—' }),
                        React.createElement(Row, { label: tr('row.game'), value: m.game && m.game !== 'default' ? (m.game_name || m.game) : tr('row.game.unknown') }),
                        React.createElement(Row, { label: tr('row.levels'), value: m.game_levels && m.game_levels.length ? Array.from(new Set(m.game_levels.slice(-8).map((v) => Math.round(Number(v))))).sort((a, b) => a - b).join(', ') + ' W' : tr('row.levels.none') }),
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
                                React.createElement("div", { style: { width: '100%' } },
                                    React.createElement(CurveGraph, { points: curveFromConfig(cfg), height: 150, now: { t: f.current_temperature != null ? safeNum(f.current_temperature, 0) : null,
                                            s: f.pwm_percent?.length && f.pwm_percent[0] != null ? safeNum(f.pwm_percent[0], 0) : null } }),
                                    f.current_temperature != null && React.createElement("div", { style: { fontSize: 12, color: '#ffb347', textAlign: 'right' } }, tr('curve.now', safeNum(f.current_temperature, 0).toFixed(0), f.pwm_percent?.length && f.pwm_percent[0] != null ? safeNum(f.pwm_percent[0], 0).toFixed(0) : '—')))),
                            React.createElement(ui.PanelSectionRow, null,
                                React.createElement(ui.ButtonItem, { layout: "below", onClick: () => {
                                        const lang = cfg.language;
                                        ui.showModal(React.createElement(FanCurveModal, { initial: curveFromConfig(cfg), tr: (k, ...a) => translate(lang, k, ...a), now: { t: f.current_temperature != null ? safeNum(f.current_temperature, 0) : null, s: null }, onSave: async (pts) => {
                                                const obj = {};
                                                pts.forEach(p => { obj[String(Math.round(p.t))] = Math.round(p.s); });
                                                const res = await rpc('set_fan_curve', { curve: obj });
                                                if (res && res.ok) {
                                                    setCurveMsg(tr('curve.saved'));
                                                    await refresh();
                                                    return { ok: true };
                                                }
                                                return { ok: false, error: (res && res.error) || tr('search.unknown') };
                                            } }));
                                    } }, tr('curve.edit'))),
                            curveMsg && React.createElement(ui.PanelSectionRow, null,
                                React.createElement("span", { style: { color: '#dbeafe' } }, curveMsg)))),
                    React.createElement(ui.PanelSection, { title: tr('section.source') },
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement("span", { style: { color: '#dbeafe' } }, tr('src.note'))),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(Row, { label: tr('src.source'), value: m.fps_source || tr('src.sourceDefault') })),
                        React.createElement(ui.PanelSectionRow, null,
                            React.createElement(ui.ToggleField, { label: tr('src.hud'), description: cfg.mangohud_display ? tr('src.hud.on') : tr('src.hud.off'), checked: !!cfg.mangohud_display, onChange: async (v) => { const ok = await rpc('set_mangohud_display', { enabled: v }); if (ok)
                                    await refresh(); } })))),
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
    // Иконка плагина: микросхема с молнией (управление мощностью чипа).
    // Цвет — currentColor, поэтому значок подсвечивается вместе с остальными в меню Decky.
    // Тот же рисунок лежит в assets/icon.svg.
    const PluginIcon = () => (React.createElement("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 24 24", width: "1em", height: "1em", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" },
        React.createElement("rect", { x: "4.5", y: "4.5", width: "15", height: "15", rx: "2.8" }),
        React.createElement("path", { d: "M9.5 1.8v2.7M14.5 1.8v2.7M9.5 19.5v2.7M14.5 19.5v2.7M1.8 9.5h2.7M1.8 14.5h2.7M19.5 9.5h2.7M19.5 14.5h2.7" }),
        React.createElement("path", { d: "M13.7 6.6 8.3 13h3.6l-1.6 4.4L15.7 11h-3.6z", fill: "currentColor", stroke: "none" })));
    function createPlugin(serverAPI) {
        const Content = makeContent(serverAPI);
        return {
            title: React.createElement("div", { className: ui.staticClasses?.Title || '' }, "GPD5CachyAutoTDP"),
            content: React.createElement(Content, null),
            icon: React.createElement(PluginIcon, null),
            onDismount() { }
        };
    }

    return createPlugin;

})(SP_REACT, DFL);
AutoTDP_Plugin
