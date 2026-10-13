// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import React, { useEffect, useRef, useState } from 'react';
import { PanelSection, PanelSectionRow, SliderField, ToggleField, ButtonItem, staticClasses } from '@decky/ui';
import { translate } from './i18n';

type ServerAPI = { callPluginMethod: (method: string, args?: Record<string, unknown>) => Promise<any> };

const DEFAULT_CONFIG = {
  enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 80, initial_tdp: 35, load_boost_enabled: true, load_boost_threshold: 95, mangohud_display: false, language: 'en',
  check_interval_sec: 3, hysteresis_threshold: 5,
  fan_control: { enabled: true },
};

const LOOKS_LIKE_CONFIG = ['enabled','target_fps','min_tdp','max_tdp','initial_tdp','fan_control'];
const looksLikeConfig = (o: any): boolean => LOOKS_LIKE_CONFIG.filter(k => Object.prototype.hasOwnProperty.call(o,k)).length >= 2;

// Разворачивает legacy-конверт Decky {result, success}. Строку ошибки бэкенда
// (success:false) не принимаем за данные — возвращаем {__error}.
const unwrap = (v: any): any => {
  let value = v;
  for (let depth = 0; depth < 4; depth++) {
    if (typeof value === 'string') {
      try { value = JSON.parse(value); continue; } catch { return value; }
    }
    if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
    if (value.success === false) {
      return { __error: typeof value.result === 'string' ? value.result : JSON.stringify(value.result) };
    }
    if (looksLikeConfig(value)) return value;
    if (Object.prototype.hasOwnProperty.call(value, 'result')) { value = value.result; continue; }
    if (Object.prototype.hasOwnProperty.call(value, 'data')) { value = value.data; continue; }
    return value;
  }
  return value;
};

const describe = (v: any): string =>
  v === undefined ? 'undefined' : v === null ? 'null' : typeof v === 'string' ? v : JSON.stringify(v);

const safeNum = (v: any, fallback: number) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

const Row = ({label,value}: {label:string; value:any}) => (
  <PanelSectionRow>
    <div style={{display:'flex',justifyContent:'space-between',width:'100%',gap:12}}>
      <span>{label}</span><span style={{fontFamily:'monospace'}}>{value == null ? '—' : String(value)}</span>
    </div>
  </PanelSectionRow>
);

function makeContent(serverAPI: ServerAPI) {
  const rpc = async (method:string,args:Record<string,unknown>={}) => {
    try {
      const raw = await serverAPI.callPluginMethod(method,args);
      const result = unwrap(raw);
      console.log('[AutoTDP] RPC', method, result);
      return result;
    } catch (e) {
      console.error('[AutoTDP] RPC',method,e);
      return null;
    }
  };

  return function Content() {
    const [cfg,setCfg] = useState<any>(null);
    const [stats,setStats] = useState<any>(null);
    const [error,setError] = useState<string>('');
    const tr = (key:string, ...args:Array<string|number>) => translate(cfg&&cfg.language, key, ...args);
    const pendingTimers = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({});
    const refreshBlockedUntil = useRef(0);

    const refresh = async () => {
      if (Date.now() < refreshBlockedUntil.current) return;
      const c = await rpc('get_config');
      if (c && c.__error) { setError(tr('err.getConfig', c.__error)); return; }
      if (c && typeof c === 'object' && !Array.isArray(c)) {
        setError(c._backend_error ? tr('err.backend', c._backend_error) : '');
        setCfg({...DEFAULT_CONFIG,...c,fan_control:{...DEFAULT_CONFIG.fan_control,...(c.fan_control||{})}});
      } else {
        setError(tr('err.getConfig', describe(c)));
        return;
      }
      const s = await rpc('get_stats');
      if (s && typeof s === 'object') setStats(s);
      else setError(tr('err.getStats'));
    };

    useEffect(() => {
      refresh();
      const timer=setInterval(refresh,2000);
      return () => clearInterval(timer);
    },[]);

    if (!cfg) return <PanelSection title={tr('section.fps')}><PanelSectionRow><span>{error || tr('status.connecting')}</span></PanelSectionRow></PanelSection>;

    const save = async (key:string,value:any) => {
      setCfg((x:any)=>({...x,[key]:value}));
      const ok=await rpc('set_config_value',{key,value});
      if (!ok) setError(tr('err.save'));
      return ok;
    };

    const updateMonitorParam = (key:string,value:any) => {
      setCfg((x:any)=>({...x,[key]:value}));
      const oldTimer = pendingTimers.current[key];
      if (oldTimer) clearTimeout(oldTimer);
      refreshBlockedUntil.current = Date.now() + 700;
      pendingTimers.current[key] = setTimeout(async () => {
        const args:any = {};
        if (key==='min_tdp') args.min_tdp=safeNum(value,15);
        else if (key==='max_tdp') args.max_tdp=safeNum(value,80);
        else if (key==='target_fps') args.target_fps=safeNum(value,40);
        else { await save(key,value); return; }
        const ok=await rpc('update_monitor_params',args);
        if (!ok) setError(tr('err.params'));
        refreshBlockedUntil.current = Date.now() + 500;
      },250);
    };

    const enabled=!!cfg.enabled;
    const toggle=async (value:boolean) => {
      const ok=value
        ? await rpc('start_monitor',{min_tdp:safeNum(cfg.min_tdp,15),max_tdp:safeNum(cfg.max_tdp,80),target_fps:safeNum(cfg.target_fps,40),enable_auto:true})
        : await rpc('stop_monitor');
      if (!ok) { setError(tr('err.toggle')); return; }
      await save('enabled',value);
      await refresh();
    };

    const t=(stats&&stats.tdp)||{};
    const m=(stats&&stats.monitor)||{};
    const f=(stats&&stats.fan)||{};
    const target=safeNum(cfg.target_fps,40);
    const minTdp=safeNum(cfg.min_tdp,15);
    const maxTdp=Math.min(80,safeNum(cfg.max_tdp,80));
    const initialTdp=safeNum(cfg.initial_tdp,35);

    return <>
      <PanelSection title="Auto TDP">
        <PanelSectionRow>
          <ToggleField label="Auto TDP" description={enabled?'Running':'Stopped'} checked={enabled} onChange={toggle}/>
        </PanelSectionRow>
      </PanelSection>
      {error && <PanelSection title="Status"><PanelSectionRow><span style={{color:'#ffb3b3'}}>{error}</span></PanelSectionRow></PanelSection>}
      <PanelSection title="Auto TDP / FPS">
        <Row label={tr('row.build')} value={(stats&&stats.build) || tr('row.build.old')}/>
        <Row label={tr('row.tdpBackend')} value={t.backend || 'none'}/>
        <Row label={tr('row.currentTdp')} value={t.current_tdp!=null ? `${safeNum(t.current_tdp,0).toFixed(1)} W` : '—'}/>
        <Row label={tr('row.tdpSource')} value={t.tdp_source==='setpoint' ? tr('row.tdpSource.setpoint') : (t.tdp_source || '—')}/>
        <Row label={tr('row.avgFps')} value={m.last_fps!=null ? safeNum(m.last_fps,0).toFixed(1) : '—'}/>
        <Row label={tr('row.effectiveGoal')} value={m.effective_target_fps!=null ? String(m.effective_target_fps) : '—'}/>
        <Row label={tr('row.tdpDecision')} value={m.tdp_hold_level!=null ? tr('row.tdpCapped', m.tdp_hold_level) : (m.tdp_decision || '—')}/>
        <Row label={tr('row.cpuLoad')} value={m.last_cpu_load!=null ? `${safeNum(m.last_cpu_load,0).toFixed(1)}%` : '—'}/>
        <Row label={tr('row.gpuLoad')} value={m.last_gpu_load!=null ? `${safeNum(m.last_gpu_load,0).toFixed(1)}%` : '—'}/>
        <Row label={tr('row.controller')} value={m.state || tr('row.controller.stopped')}/>
        <PanelSectionRow><SliderField label={tr('slider.targetFps')} value={target} min={30} max={120} step={5} showValue onChange={(v:number)=>updateMonitorParam('target_fps',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label={tr('slider.startTdp')} description={enabled?tr('slider.startTdp.on'):tr('slider.startTdp.off')} value={initialTdp} min={5} max={80} step={1} showValue valueSuffix=" W" onChange={async(v:number)=>{const ok=await save('initial_tdp',v);if(ok && !enabled) await rpc('set_tdp',{value:v});}}/></PanelSectionRow>
        <PanelSectionRow><SliderField label={tr('slider.minTdp')} value={minTdp} min={5} max={maxTdp} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('min_tdp',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label={tr('slider.maxTdp')} value={maxTdp} min={minTdp} max={80} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('max_tdp',v)}/></PanelSectionRow>
        <PanelSectionRow><ToggleField label={tr('toggle.loadBoost')} description={cfg.load_boost_enabled?tr('toggle.loadBoost.on', safeNum(cfg.load_boost_threshold,95)):tr('toggle.loadBoost.off')} checked={!!cfg.load_boost_enabled} onChange={async(v:boolean)=>{const ok=await save('load_boost_enabled',v);if(ok) await refresh();}}/></PanelSectionRow>
        <PanelSectionRow><SliderField label={tr('slider.threshold')} value={safeNum(cfg.load_boost_threshold,95)} min={90} max={100} step={1} showValue valueSuffix="%" onChange={(v:number)=>save('load_boost_threshold',v)}/></PanelSectionRow>
      </PanelSection>

      <PanelSection title={tr('section.fan')}>
        <Row label={tr('fan.controller')} value={f.available?tr('fan.controller.ok'):tr('fan.controller.none')}/>
        <Row label={tr('fan.temp')} value={f.current_temperature!=null ? `${safeNum(f.current_temperature,0).toFixed(1)} °C` : '—'}/>
        <Row label={tr('fan.channels')} value={f.channels || 0}/>
        <Row label={tr('fan.rpm')} value={f.fan_rpm?.length ? f.fan_rpm.map((v:any)=>v==null?'—':v).join(', ') : '—'}/>
        <Row label={tr('fan.pwm')} value={f.pwm_percent?.length ? f.pwm_percent.map((v:any)=>v==null?'—':`${v.toFixed(1)}%`).join(', ') : '—'}/>
        <PanelSectionRow>
          <ToggleField label={tr('fan.control')} description={cfg.fan_control?.enabled?tr('fan.control.on'):tr('fan.control.off')} checked={!!cfg.fan_control?.enabled} disabled={!f.available} onChange={async(v:boolean)=>{const ok=await rpc(v?'enable_fan_control':'disable_fan_control');if(ok) await refresh();}}/>
        </PanelSectionRow>
        {!f.available && <PanelSectionRow><span style={{color:'#94a3b8'}}>{tr('fan.notDetected')}</span></PanelSectionRow>}
      </PanelSection>

      <PanelSection title={tr('section.source')}>
        <PanelSectionRow><span style={{color:'#dbeafe'}}>{tr('src.note')}</span></PanelSectionRow>
        <PanelSectionRow><Row label={tr('src.source')} value={m.fps_source || tr('src.sourceDefault')}/></PanelSectionRow>
        <PanelSectionRow>
          <ToggleField label={tr('src.hud')} description={cfg.mangohud_display?tr('src.hud.on'):tr('src.hud.off')} checked={!!cfg.mangohud_display} onChange={async(v:boolean)=>{const ok=await rpc('set_mangohud_display',{enabled:v});if(ok) await refresh();}}/>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title={tr('lang.title')}>
        <PanelSectionRow>
          <ToggleField label={tr('lang.en')} description={cfg.language==='en' ? '✓' : ''} checked={cfg.language==='en'} onChange={async(v:boolean)=>{if(!v) return; const ok=await rpc('set_language',{language:'en'}); if(ok) await refresh(); else setError(tr('err.lang'));}}/>
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField label={tr('lang.ru')} description={cfg.language==='ru' ? '✓' : ''} checked={cfg.language==='ru'} onChange={async(v:boolean)=>{if(!v) return; const ok=await rpc('set_language',{language:'ru'}); if(ok) await refresh(); else setError(tr('err.lang'));}}/>
        </PanelSectionRow>
      </PanelSection>
    </>;
  };
}

export default function createPlugin(serverAPI: ServerAPI) {
  const Content=makeContent(serverAPI);
  return {
    title:<div className={staticClasses?.Title || ''}>GPD5CachyAutoTDP</div>,
    content:<Content/>,
    icon:<span>⚡</span>,
    onDismount(){}
  };
}
