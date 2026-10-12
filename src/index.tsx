// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import React, { useEffect, useRef, useState } from 'react';
import { PanelSection, PanelSectionRow, SliderField, ToggleField, ButtonItem, staticClasses } from '@decky/ui';

type ServerAPI = { callPluginMethod: (method: string, args?: Record<string, unknown>) => Promise<any> };

const DEFAULT_CONFIG = {
  enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 80, initial_tdp: 35, load_boost_enabled: true, load_boost_threshold: 95, mangohud_display: false,
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
    const [coresDraft,setCoresDraft]=useState<number|null>(null);
    const [error,setError] = useState<string>('');
    const pendingTimers = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({});
    const refreshBlockedUntil = useRef(0);

    const refresh = async () => {
      if (Date.now() < refreshBlockedUntil.current) return;
      const c = await rpc('get_config');
      if (c && c.__error) { setError('Backend RPC get_config вернул неверный ответ: ' + c.__error); return; }
      if (c && typeof c === 'object' && !Array.isArray(c)) {
        setError(c._backend_error ? 'AutoTDP backend: ' + c._backend_error : '');
        setCfg({...DEFAULT_CONFIG,...c,fan_control:{...DEFAULT_CONFIG.fan_control,...(c.fan_control||{})}});
      } else {
        setError('Backend RPC get_config вернул неверный ответ: ' + describe(c));
        return;
      }
      const s = await rpc('get_stats');
      if (s && typeof s === 'object') setStats(s);
      else setError('Backend RPC get_stats не отвечает');
    };

    useEffect(() => {
      refresh();
      const timer=setInterval(refresh,2000);
      return () => clearInterval(timer);
    },[]);

    if (!cfg) return <PanelSection title="Auto TDP / FPS"><PanelSectionRow><span>{error || 'Подключение к backend…'}</span></PanelSectionRow></PanelSection>;

    const save = async (key:string,value:any) => {
      setCfg((x:any)=>({...x,[key]:value}));
      const ok=await rpc('set_config_value',{key,value});
      if (!ok) setError('Backend не принял изменение');
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
        if (!ok) setError('Backend не принял параметры AutoTDP');
        refreshBlockedUntil.current = Date.now() + 500;
      },250);
    };

    const enabled=!!cfg.enabled;
    const toggle=async (value:boolean) => {
      const ok=value
        ? await rpc('start_monitor',{min_tdp:safeNum(cfg.min_tdp,15),max_tdp:safeNum(cfg.max_tdp,80),target_fps:safeNum(cfg.target_fps,40),enable_auto:true})
        : await rpc('stop_monitor');
      if (!ok) { setError('Не удалось изменить состояние AutoTDP'); return; }
      await save('enabled',value);
      await refresh();
    };

    const t=(stats&&stats.tdp)||{};
    const m=(stats&&stats.monitor)||{};
    const f=(stats&&stats.fan)||{};
    const coresStatusText=(op:any,draft:number|null)=>{
      if(!op) return '';
      if(op.state==='running') return `Изменение ядер: ${op.stage||'выполняется'}${op.detail?` — ${op.detail}`:''}…`;
      if(op.state==='done') return `Готово: активно ${op.result&&op.result.applied} физ. ядер`;
      if(op.state==='error') return `Не выполнено: ${(op.result&&op.result.error)||'неизвестная ошибка'}`;
      return draft!=null ? `Запрошено ${draft} ядер` : '';
    };
    const c_={available:false,min_cores:2,max_cores:0,active_cores:0,online_threads:0,total_threads:0,...((stats&&stats.cores)||{})};
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
        <Row label="Build" value={(stats&&stats.build) || 'старый backend: переустановите архив'}/>
        <Row label="TDP backend" value={t.backend || 'none'}/>
        <Row label="Current TDP" value={t.current_tdp!=null ? `${safeNum(t.current_tdp,0).toFixed(1)} W` : '—'}/>
        <Row label="TDP source" value={t.tdp_source==='setpoint' ? 'setpoint (ryzenadj readback unavailable)' : (t.tdp_source || '—')}/>
        <Row label="Average FPS" value={m.last_fps!=null ? safeNum(m.last_fps,0).toFixed(1) : '—'}/>
        <Row label="Effective FPS goal" value={m.effective_target_fps!=null ? String(m.effective_target_fps) : '—'}/>
        <Row label="TDP decision" value={m.tdp_hold_level!=null ? `capped at ${m.tdp_hold_level} W` : (m.tdp_decision || '—')}/>
        <Row label="Core evacuation" value={c_.evacuation ? (c_.evacuation.ok ? `ok, ${c_.evacuation.moved_threads||0} threads moved` : `blocked: ${c_.evacuation_stuck||0} threads stuck`) : '—'}/>
        <Row label="CPU load" value={m.last_cpu_load!=null ? `${safeNum(m.last_cpu_load,0).toFixed(1)}%` : '—'}/>
        <Row label="GPU load" value={m.last_gpu_load!=null ? `${safeNum(m.last_gpu_load,0).toFixed(1)}%` : '—'}/>
        <Row label="Controller" value={m.state || 'stopped'}/>
        <PanelSectionRow><SliderField label="Target FPS" value={target} min={30} max={120} step={5} showValue onChange={(v:number)=>updateMonitorParam('target_fps',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Start TDP" description={enabled?'Used when Auto TDP starts':'Applied when Auto TDP is switched off'} value={initialTdp} min={5} max={80} step={1} showValue valueSuffix=" W" onChange={async(v:number)=>{const ok=await save('initial_tdp',v);if(ok && !enabled) await rpc('set_tdp',{value:v});}}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Minimum TDP" value={minTdp} min={5} max={maxTdp} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('min_tdp',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Maximum TDP" value={maxTdp} min={minTdp} max={80} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('max_tdp',v)}/></PanelSectionRow>
        {c_.available && <><PanelSectionRow><SliderField label="Active CPU cores" description={`Physical cores with SMT kept together; ${c_.online_threads}/${c_.total_threads} threads online`} value={coresDraft!=null ? coresDraft : c_.active_cores} min={c_.min_cores} max={c_.max_cores} step={1} showValue onChange={(v:number)=>{setCoresDraft(v); rpc('set_active_cores',{cores:v}).then((res:any)=>{if(!res||res.started===false)setError('Не удалось начать изменение ядер: '+((res&&res.error)||'нет ответа backend')); else setCoresDraft(v);});}}/></PanelSectionRow><PanelSectionRow><span style={{color:'#dbeafe'}}>{coresStatusText(c_.operation, coresDraft)}</span></PanelSectionRow></>}
        <PanelSectionRow><ToggleField label="High-load TDP boost" description={cfg.load_boost_enabled?`CPU >${safeNum(cfg.load_boost_threshold,95)}% boosts TDP even when FPS is already on target; GPU >${safeNum(cfg.load_boost_threshold,95)}% boosts only when FPS is below target`:'Disabled'} checked={!!cfg.load_boost_enabled} onChange={async(v:boolean)=>{const ok=await save('load_boost_enabled',v);if(ok) await refresh();}}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="High-load threshold" value={safeNum(cfg.load_boost_threshold,95)} min={90} max={100} step={1} showValue valueSuffix="%" onChange={(v:number)=>save('load_boost_threshold',v)}/></PanelSectionRow>
      </PanelSection>

      <PanelSection title="Fan curve">
        <Row label="Controller" value={f.available?'gpdfan / PWM':'not detected'}/>
        <Row label="Temperature" value={f.current_temperature!=null ? `${safeNum(f.current_temperature,0).toFixed(1)} °C` : '—'}/>
        <Row label="Channels" value={f.channels || 0}/>
        <Row label="Fan RPM" value={f.fan_rpm?.length ? f.fan_rpm.map((v:any)=>v==null?'—':v).join(', ') : '—'}/>
        <Row label="PWM" value={f.pwm_percent?.length ? f.pwm_percent.map((v:any)=>v==null?'—':`${v.toFixed(1)}%`).join(', ') : '—'}/>
        <PanelSectionRow>
          <ToggleField label="Fan control" description={cfg.fan_control?.enabled?'Curve enabled':'Curve disabled'} checked={!!cfg.fan_control?.enabled} disabled={!f.available} onChange={async(v:boolean)=>{const ok=await rpc(v?'enable_fan_control':'disable_fan_control');if(ok) await refresh();}}/>
        </PanelSectionRow>
        {!f.available && <PanelSectionRow><span style={{color:'#94a3b8'}}>PWM fan controller not detected.</span></PanelSectionRow>}
      </PanelSection>

      <PanelSection title="FPS source / requirements">
        <PanelSectionRow><span style={{color:'#dbeafe'}}>Keep system MangoHud enabled. For correct AutoTDP behavior, disable FPS limits both in the game and in the system/gamescope. The plugin needs uncapped FPS to see the real performance headroom.</span></PanelSectionRow>
        <PanelSectionRow><Row label="Source" value={m.fps_source || 'MangoHud / mangoapp CSV'}/></PanelSectionRow>
        <PanelSectionRow>
          <ToggleField label="MangoHud display" description={cfg.mangohud_display?'HUD visible':'HUD hidden (logging remains active)'} checked={!!cfg.mangohud_display} onChange={async(v:boolean)=>{const ok=await rpc('set_mangohud_display',{enabled:v});if(ok) await refresh();}}/>
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
