// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import React, { useEffect, useState } from 'react';
import { PanelSection, PanelSectionRow, SliderField, ToggleField, ButtonItem, staticClasses } from '@decky/ui';

type ServerAPI = { callPluginMethod: (method: string, args?: Record<string, unknown>) => Promise<any> };

const DEFAULT_CONFIG = {
  enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 55, initial_tdp: 35, mangohud_display: false,
  check_interval_sec: 3, hysteresis_threshold: 5,
  fan_control: { enabled: true },
};

const unwrap = (v: any): any => {
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    if (Object.prototype.hasOwnProperty.call(v, 'result') &&
        (Object.prototype.hasOwnProperty.call(v, 'success') || Object.keys(v).length <= 2)) return v.result;
    if (Object.prototype.hasOwnProperty.call(v, 'data') &&
        (Object.prototype.hasOwnProperty.call(v, 'success') || Object.keys(v).length <= 2)) return v.data;
  }
  return v;
};

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

    const refresh = async () => {
      const c = await rpc('get_config');
      if (c && typeof c === 'object' && !Array.isArray(c)) {
        setCfg({...DEFAULT_CONFIG,...c,fan_control:{...DEFAULT_CONFIG.fan_control,...(c.fan_control||{})}});
      } else {
        setError('Backend RPC get_config вернул неверный ответ');
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

    const updateMonitorParam = async (key:string,value:any) => {
      setCfg((x:any)=>({...x,[key]:value}));
      const args:any = {};
      if (key==='min_tdp') args.min_tdp=safeNum(value,15);
      else if (key==='max_tdp') args.max_tdp=safeNum(value,55);
      else if (key==='target_fps') args.target_fps=safeNum(value,40);
      else return save(key,value);
      const ok=await rpc('update_monitor_params',args);
      if (!ok) setError('Backend не принял параметры AutoTDP');
      return ok;
    };

    const enabled=!!cfg.enabled;
    const toggle=async (value:boolean) => {
      const ok=value
        ? await rpc('start_monitor',{min_tdp:safeNum(cfg.min_tdp,15),max_tdp:safeNum(cfg.max_tdp,55),target_fps:safeNum(cfg.target_fps,40),enable_auto:true})
        : await rpc('stop_monitor');
      if (!ok) { setError('Не удалось изменить состояние AutoTDP'); return; }
      await save('enabled',value);
      await refresh();
    };

    const t=(stats&&stats.tdp)||{};
    const m=(stats&&stats.monitor)||{};
    const f=(stats&&stats.fan)||{};
    const target=safeNum(cfg.target_fps,40);
    const minTdp=safeNum(cfg.min_tdp,15);
    const maxTdp=safeNum(cfg.max_tdp,55);
    const initialTdp=safeNum(cfg.initial_tdp,35);

    return <>
      {error && <PanelSection title="Status"><PanelSectionRow><span style={{color:'#ffb3b3'}}>{error}</span></PanelSectionRow></PanelSection>}
      <PanelSection title="Auto TDP / FPS">
        <Row label="TDP backend" value={t.backend || 'none'}/>
        <Row label="Current TDP" value={t.current_tdp!=null ? `${safeNum(t.current_tdp,0).toFixed(1)} W` : '—'}/>
        <Row label="TDP source" value={t.tdp_source==='setpoint' ? 'setpoint (ryzenadj readback unavailable)' : (t.tdp_source || '—')}/>
        <Row label="Average FPS" value={m.last_fps!=null ? safeNum(m.last_fps,0).toFixed(1) : '—'}/>
        <Row label="Controller" value={m.state || 'stopped'}/>
        <PanelSectionRow>
          <ToggleField label="Auto TDP" description={enabled?'Running':'Stopped'} checked={enabled} onChange={toggle}/>
        </PanelSectionRow>
        <PanelSectionRow><SliderField label="Target FPS" value={target} min={30} max={120} step={5} showValue onChange={(v:number)=>updateMonitorParam('target_fps',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Start TDP" description="Used when no previous AutoTDP setpoint exists" value={initialTdp} min={5} max={55} step={1} showValue valueSuffix=" W" onChange={(v:number)=>save('initial_tdp',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Minimum TDP" value={minTdp} min={5} max={maxTdp} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('min_tdp',v)}/></PanelSectionRow>
        <PanelSectionRow><SliderField label="Maximum TDP" value={maxTdp} min={minTdp} max={55} step={1} showValue valueSuffix=" W" onChange={(v:number)=>updateMonitorParam('max_tdp',v)}/></PanelSectionRow>
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

      <PanelSection title="FPS source">
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
