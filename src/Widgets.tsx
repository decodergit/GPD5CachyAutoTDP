// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
//
// Элементы панели (3.7.0): сводка, строка состояния, график за минуту,
// сворачиваемые блоки и компактные строки диагностики.
import React from 'react';
import { ButtonItem, PanelSectionRow } from '@decky/ui';

export const COLORS = {
  text: '#dcdedf',
  dim: '#8b929a',
  accent: '#1a9fff',
  tdp: '#ffb347',
  ok: '#5ba32b',
  warn: '#e5b13a',
  bad: '#e35e5e',
  card: 'rgba(255,255,255,0.05)',
};

// --- сводка ---------------------------------------------------------------------
type Tile = { label: string; value: string; sub?: string; color?: string };

export function Tiles({ tiles }: { tiles: Tile[] }) {
  return (
    <div style={{ display: 'flex', gap: 6, width: '100%' }}>
      {tiles.map((t, i) => (
        <div key={i} style={{ flex: 1, background: COLORS.card, borderRadius: 6, padding: '6px 4px', textAlign: 'center', minWidth: 0 }}>
          <div style={{ fontSize: 11, color: COLORS.dim, textTransform: 'uppercase', letterSpacing: 0.5 }}>{t.label}</div>
          <div style={{ fontSize: 22, fontWeight: 600, color: t.color || COLORS.text, lineHeight: '26px' }}>{t.value}</div>
          <div style={{ fontSize: 11, color: COLORS.dim, minHeight: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.sub || ''}</div>
        </div>
      ))}
    </div>
  );
}

export type Tone = 'ok' | 'warn' | 'bad' | 'dim';

export function StatusLine({ text, tone }: { text: string; tone: Tone }) {
  const color = tone === 'ok' ? COLORS.ok : tone === 'warn' ? COLORS.warn : tone === 'bad' ? COLORS.bad : COLORS.dim;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: COLORS.text, marginTop: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: color, flex: 'none' }} />
      <span>{text}</span>
    </div>
  );
}

// --- график за минуту ---------------------------------------------------------------
type HistoryPoint = [number, number, number];   // [секунд назад, fps, tdp]

export function HistoryChart({ history, goal, maxTdp, legend, unitW }: {
  history: HistoryPoint[]; goal: number | null; maxTdp: number; legend: string; unitW: string;
}) {
  const W = 300, H = 64, SPAN = 60;
  const pts = (history || []).filter(p => Array.isArray(p) && p[0] <= SPAN);
  if (pts.length < 2) return null;
  const fpsMax = Math.max(goal ? goal * 1.5 : 60, ...pts.map(p => p[1])) * 1.05;
  const tdpMax = Math.max(maxTdp, ...pts.map(p => p[2]));
  const x = (age: number) => W - age / SPAN * W;
  const yF = (f: number) => H - 2 - Math.min(f, fpsMax) / fpsMax * (H - 4);
  const yW = (w: number) => H - 2 - Math.min(w, tdpMax) / tdpMax * (H - 4);
  const line = (sel: (p: HistoryPoint) => number) =>
    pts.map(p => `${x(p[0]).toFixed(1)},${sel(p).toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  return (
    <div style={{ marginTop: 6 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', background: 'rgba(0,0,0,0.25)', borderRadius: 4 }}>
        {goal != null && <line x1={0} x2={W} y1={yF(goal)} y2={yF(goal)} stroke={COLORS.accent} strokeOpacity={0.5} strokeDasharray="4 3" />}
        <polyline points={line(p => yW(p[2]))} fill="none" stroke={COLORS.tdp} strokeWidth={1.8} strokeLinejoin="round" />
        <polyline points={line(p => yF(p[1]))} fill="none" stroke={COLORS.accent} strokeWidth={1.8} strokeLinejoin="round" />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: COLORS.dim, marginTop: 2 }}>
        <span><span style={{ color: COLORS.accent }}>━ FPS {last[1].toFixed(0)}</span>{'  '}<span style={{ color: COLORS.tdp }}>━ TDP {last[2].toFixed(0)} {unitW}</span></span>
        <span>{legend}</span>
      </div>
    </div>
  );
}

// --- сворачиваемые блоки ---------------------------------------------------------------
// Состояние раскрытия живёт, пока плагин загружен: при повторном открытии меню
// блоки остаются такими, какими их оставили.
const OPEN: Record<string, boolean> = {};

export function useFold(id: string): [boolean, () => void] {
  const [open, setOpen] = React.useState<boolean>(!!OPEN[id]);
  return [open, () => { OPEN[id] = !open; setOpen(!open); }];
}

export function FoldHeader({ title, open, onToggle }: { title: string; open: boolean; onToggle: () => void }) {
  return (
    <PanelSectionRow>
      <ButtonItem layout="below" onClick={onToggle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
          <span>{title}</span><span style={{ color: COLORS.dim }}>{open ? '▴' : '▾'}</span>
        </div>
      </ButtonItem>
    </PanelSectionRow>
  );
}

// --- строки --------------------------------------------------------------------------------
export function InfoRow({ label, value }: { label: string; value: any }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12, padding: '2px 0' }}>
      <span style={{ color: COLORS.dim }}>{label}</span>
      <span style={{ textAlign: 'right', wordBreak: 'break-word' }}>{value == null || value === '' ? '—' : String(value)}</span>
    </div>
  );
}

export function Banner({ text, tone = 'bad' }: { text: string; tone?: Tone }) {
  const color = tone === 'warn' ? COLORS.warn : COLORS.bad;
  return (
    <div style={{ borderLeft: `3px solid ${color}`, background: 'rgba(255,255,255,0.04)', padding: '6px 8px', fontSize: 12, color: COLORS.text, borderRadius: 3 }}>
      {text}
    </div>
  );
}
