// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
//
// Кривая вентилятора в виде графика (3.5.0): компактный график в панели и редактор
// в модальном окне. Точки перетаскиваются пальцем, касание пустого места добавляет точку;
// для геймпада есть переключение точек и ползунки выбранной точки.
import React, { useRef, useState } from 'react';
import { ModalRoot, DialogButton, SliderField, Focusable } from '@decky/ui';

export type CurvePoint = { t: number; s: number };
type Tr = (key: string, ...args: Array<string | number>) => string;

// Границы совпадают с FanController.validate_curve.
export const T_MIN = 20, T_MAX = 110, S_MIN = 0, S_MAX = 100;
// Совпадает с FanController.DEFAULT_CURVE.
export const DEFAULT_CURVE: CurvePoint[] = [
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

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

function geometry(height: number) {
  const pw = VB_W - PAD.l - PAD.r;
  const ph = height - PAD.t - PAD.b;
  return {
    pw, ph,
    x: (t: number) => PAD.l + (t - T_MIN) / (T_MAX - T_MIN) * pw,
    y: (s: number) => PAD.t + (1 - (s - S_MIN) / (S_MAX - S_MIN)) * ph,
    t: (px: number) => T_MIN + (px - PAD.l) / pw * (T_MAX - T_MIN),
    s: (py: number) => S_MIN + (1 - (py - PAD.t) / ph) * (S_MAX - S_MIN),
  };
}

// --- данные -------------------------------------------------------------------
/** Сортирует, склеивает одинаковые температуры (берёт бо́льшую скорость), делает кривую неубывающей. */
export function normalizeCurve(pts: CurvePoint[]): CurvePoint[] {
  const byT: Record<number, number> = {};
  pts.forEach(p => {
    const t = Math.round(clamp(Number(p.t), T_MIN, T_MAX));
    const s = Math.round(clamp(Number(p.s), S_MIN, S_MAX));
    if (!Number.isFinite(t) || !Number.isFinite(s)) return;
    byT[t] = byT[t] === undefined ? s : Math.max(byT[t], s);
  });
  const out = Object.keys(byT).map(k => ({ t: Number(k), s: byT[Number(k)] })).sort((a, b) => a.t - b.t);
  for (let i = 1; i < out.length; i++) out[i].s = Math.max(out[i].s, out[i - 1].s);
  return out;
}

/** Скорость по кривой при температуре t (как FanController.calc). */
export function curveAt(pts: CurvePoint[], t: number): number {
  if (!pts.length) return S_MAX;
  if (t <= pts[0].t) return pts[0].s;
  if (t >= pts[pts.length - 1].t) return pts[pts.length - 1].s;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (t <= b.t) return a.s + (t - a.t) * (b.s - a.s) / (b.t - a.t);
  }
  return pts[pts.length - 1].s;
}

/** Ставит точку i в (t, s): температура между соседями, скорость «толкает» соседей,
 *  чтобы кривая оставалась неубывающей. */
function movePoint(pts: CurvePoint[], i: number, t: number, s: number): CurvePoint[] {
  const out = pts.map(p => ({ ...p }));
  const lo = i > 0 ? out[i - 1].t + 1 : T_MIN;
  const hi = i < out.length - 1 ? out[i + 1].t - 1 : T_MAX;
  out[i].t = Math.round(clamp(t, lo, hi));
  out[i].s = Math.round(clamp(s, S_MIN, S_MAX));
  for (let j = i + 1; j < out.length; j++) out[j].s = Math.max(out[j].s, out[i].s);
  for (let j = i - 1; j >= 0; j--) out[j].s = Math.min(out[j].s, out[i].s);
  return out;
}

function addPoint(pts: CurvePoint[], t: number, s: number): { pts: CurvePoint[]; index: number } | null {
  const tt = Math.round(clamp(t, T_MIN, T_MAX));
  if (pts.some(p => p.t === tt)) return null;
  const out = [...pts.map(p => ({ ...p })), { t: tt, s: 0 }].sort((a, b) => a.t - b.t);
  const index = out.findIndex(p => p.t === tt);
  return { pts: movePoint(out, index, tt, s), index };
}

// --- график ----------------------------------------------------------------------
type Now = { t: number | null; s: number | null };

type GraphProps = {
  points: CurvePoint[];
  now?: Now;
  height: number;
  selected?: number | null;
  svgRef?: React.Ref<SVGSVGElement>;
  handlers?: React.SVGProps<SVGSVGElement>;
};

export function CurveGraph({ points, now, height, selected = null, svgRef, handlers }: GraphProps) {
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

  return (
    <svg ref={svgRef} viewBox={`0 0 ${VB_W} ${height}`} width="100%"
      style={{ display: 'block', touchAction: 'none', userSelect: 'none' }} {...handlers}>
      <rect x={PAD.l} y={PAD.t} width={g.pw} height={g.ph} fill="rgba(0,0,0,0.25)" rx={3} />
      {[20, 40, 60, 80, 100].map(t => <line key={`gt${t}`} x1={g.x(t + 10)} x2={g.x(t + 10)} y1={PAD.t} y2={PAD.t + g.ph} stroke={GRID} />)}
      {sTicks.map(s => <line key={`gs${s}`} x1={PAD.l} x2={PAD.l + g.pw} y1={g.y(s)} y2={g.y(s)} stroke={GRID} />)}
      {tTicks.map(t => <text key={`lt${t}`} x={g.x(t)} y={height - 5} fill={LABEL} fontSize={11} textAnchor="middle">{t}°</text>)}
      {sTicks.map(s => <text key={`ls${s}`} x={PAD.l - 4} y={g.y(s) + 4} fill={LABEL} fontSize={11} textAnchor="end">{s}%</text>)}
      <polygon points={area} fill="rgba(26,159,255,0.16)" />
      <polyline points={lineStr} fill="none" stroke={ACCENT} strokeWidth={2.5} strokeLinejoin="round" />
      {nowT != null && <>
        <line x1={g.x(nowT)} x2={g.x(nowT)} y1={PAD.t} y2={PAD.t + g.ph} stroke={NOW} strokeWidth={1.5} strokeDasharray="4 3" />
        <circle cx={g.x(nowT)} cy={g.y(nowS as number)} r={r + 1} fill={NOW} />
      </>}
      {points.map((p, i) => (
        <circle key={i} cx={g.x(p.t)} cy={g.y(p.s)} r={i === selected ? r + 3 : r}
          fill={i === selected ? '#ffffff' : ACCENT} stroke={i === selected ? ACCENT : '#0e141b'} strokeWidth={2} />
      ))}
    </svg>
  );
}

// --- редактор в модальном окне --------------------------------------------------------
type ModalProps = {
  initial: CurvePoint[];
  now?: Now;
  tr: Tr;
  closeModal?: () => void;
  onSave: (pts: CurvePoint[]) => Promise<{ ok: boolean; error?: string }>;
};

const EDITOR_H = 250;
const HIT_RADIUS = 18;   // в единицах viewBox: пальцу нужна зона больше самой точки

export function FanCurveModal({ initial, now, tr, closeModal, onSave }: ModalProps) {
  const [points, setPoints] = useState<CurvePoint[]>(() => {
    const n = normalizeCurve(initial);
    return n.length >= 2 ? n : DEFAULT_CURVE.map(p => ({ ...p }));
  });
  const [sel, setSel] = useState(0);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<number | null>(null);
  const g = geometry(EDITOR_H);

  const toView = (e: React.PointerEvent) => {
    const rect = svgRef.current!.getBoundingClientRect();
    return {
      px: (e.clientX - rect.left) / rect.width * VB_W,
      py: (e.clientY - rect.top) / rect.height * EDITOR_H,
    };
  };

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    const { px, py } = toView(e);
    let best = -1, bestD = HIT_RADIUS;
    points.forEach((p, i) => {
      const d = Math.hypot(g.x(p.t) - px, g.y(p.s) - py);
      if (d < bestD) { best = i; bestD = d; }
    });
    if (best < 0) {
      const added = addPoint(points, g.t(px), g.s(py));
      if (!added) return;
      setPoints(added.pts);
      best = added.index;
    }
    setSel(best);
    drag.current = best;
    setMsg('');
    try { (e.currentTarget as any).setPointerCapture(e.pointerId); } catch { /* старый CEF */ }
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (drag.current == null) return;
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
    if (res && res.ok) { closeModal && closeModal(); return; }
    setMsg(tr('curve.saveFail', (res && res.error) || '?'));
  };

  return (
    <ModalRoot closeModal={closeModal} onCancel={closeModal}>
      <div style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 6 }}>{tr('curve.title')}</div>
      <CurveGraph points={points} now={now} height={EDITOR_H} selected={idx} svgRef={svgRef}
        handlers={{ onPointerDown, onPointerMove, onPointerUp: endDrag, onPointerCancel: endDrag, onPointerLeave: endDrag }} />
      <div style={{ fontSize: 12, color: LABEL, margin: '4px 0 8px' }}>{tr('curve.graphHint')}</div>
      <Focusable style={{ display: 'flex', gap: 8, alignItems: 'center' }} flow-children="horizontal">
        <DialogButton style={{ minWidth: 0, flex: 1 }} disabled={idx <= 0} onClick={() => setSel(idx - 1)}>{tr('curve.prev')}</DialogButton>
        <div style={{ flex: 2, textAlign: 'center', fontSize: 14 }}>{tr('curve.selected', idx + 1, points.length, cur.t, cur.s)}</div>
        <DialogButton style={{ minWidth: 0, flex: 1 }} disabled={idx >= points.length - 1} onClick={() => setSel(idx + 1)}>{tr('curve.next')}</DialogButton>
      </Focusable>
      <SliderField label={tr('curve.temp')} value={cur.t} min={tLo} max={Math.max(tLo, tHi)} step={1} showValue
        onChange={(v: number) => setPoints(prev => movePoint(prev, idx, v, prev[idx].s))} />
      <SliderField label={tr('curve.speed')} value={cur.s} min={S_MIN} max={S_MAX} step={1} showValue
        onChange={(v: number) => setPoints(prev => movePoint(prev, idx, prev[idx].t, v))} />
      <Focusable style={{ display: 'flex', gap: 8, marginTop: 10 }} flow-children="horizontal">
        <DialogButton style={{ minWidth: 0, flex: 1 }} disabled={points.length <= 2}
          onClick={() => { setPoints(points.filter((_, i) => i !== idx)); setSel(Math.max(0, idx - 1)); }}>{tr('curve.delete')}</DialogButton>
        <DialogButton style={{ minWidth: 0, flex: 1 }} onClick={() => { setPoints(DEFAULT_CURVE.map(p => ({ ...p }))); setSel(0); setMsg(''); }}>{tr('curve.reset')}</DialogButton>
      </Focusable>
      <Focusable style={{ display: 'flex', gap: 8, marginTop: 8 }} flow-children="horizontal">
        <DialogButton style={{ minWidth: 0, flex: 1 }} disabled={busy} onClick={save}>{tr('curve.save')}</DialogButton>
        <DialogButton style={{ minWidth: 0, flex: 1 }} onClick={() => closeModal && closeModal()}>{tr('curve.cancel')}</DialogButton>
      </Focusable>
      {msg && <div style={{ color: '#ffb3b3', marginTop: 8 }}>{msg}</div>}
    </ModalRoot>
  );
}
