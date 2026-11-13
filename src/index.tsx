// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import React, { useEffect, useRef, useState } from 'react';
import { PanelSection, PanelSectionRow, SliderField, ToggleField, ButtonItem, DropdownItem, staticClasses, showModal } from '@decky/ui';
import { translate } from './i18n';
import { CurveGraph, FanCurveModal, CurvePoint } from './FanCurve';
import { Banner, COLORS, FoldHeader, HistoryChart, InfoRow, StatusLine, Tiles, Tone, useFold } from './Widgets';

type ServerAPI = { callPluginMethod: (method: string, args?: Record<string, unknown>) => Promise<any> };

const DEFAULT_CONFIG = {
  plugin_enabled: true, enabled: false, target_fps: 40, min_tdp: 15, max_tdp: 80, initial_tdp: 35, load_boost_enabled: true, load_boost_threshold: 95, mangohud_display: false, language: 'auto',
  check_interval_sec: 1, hysteresis_threshold: 5,
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

const PHASE_TONE: Record<string, Tone> = {
  holding: 'ok', lowering: 'ok', probing: 'ok',
  raising: 'warn', boost: 'warn', waiting: 'warn',
  short: 'bad', off: 'dim',
};

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
    const [curveMsg,setCurveMsg]=useState<string>('');
    const [limitsOpen, toggleLimits] = useFold('limits');
    const [advOpen, toggleAdv] = useFold('advanced');
    const [diagOpen, toggleDiag] = useFold('diag');
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

    if (!cfg) return <PanelSection><PanelSectionRow><span>{error || tr('status.connecting')}</span></PanelSectionRow></PanelSection>;

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
    const toggleAuto=async (value:boolean) => {
      const ok=value
        ? await rpc('start_monitor',{min_tdp:safeNum(cfg.min_tdp,15),max_tdp:safeNum(cfg.max_tdp,80),target_fps:safeNum(cfg.target_fps,40),enable_auto:true})
        : await rpc('stop_monitor');
      if (!ok) { setError(tr('err.toggle')); return; }
      await save('enabled',value);
      await refresh();
    };

    const pluginEnabled = cfg.plugin_enabled !== false;
    // active приходит из get_stats: false, если плагин выключен или приостановлен окном tdp_gui.py.
    const pluginActive = stats ? stats.active !== false : pluginEnabled;
    const guiPid = stats && stats.gui_pid;
    const togglePlugin = async (value:boolean) => {
      setCfg((x:any)=>({...x,plugin_enabled:value}));
      const ok = await rpc('set_plugin_enabled',{enabled:value});
      if (!ok) setError(tr('err.plugin'));
      await refresh();
    };

    const t=(stats&&stats.tdp)||{};
    const m=(stats&&stats.monitor)||{};
    const f=(stats&&stats.fan)||{};
    const W=tr('unit.w');
    const curveFromConfig=(c:any)=>{
      const cur=(c&&c.fan_control&&c.fan_control.curve)||{};
      const byTemp:Record<number,number>={};
      Object.keys(cur).forEach((k:any)=>{
        const tt=Number(k), s=Number(cur[k]);
        if(!Number.isFinite(tt)||!Number.isFinite(s)) return;
        // Несколько значений на одну температуру (старый формат, ручная правка):
        // оставляем максимум — выше скорость безопаснее.
        byTemp[tt]=byTemp[tt]===undefined?Math.max(0,Math.min(100,s)):Math.max(byTemp[tt],Math.max(0,Math.min(100,s)));
      });
      const arr=Object.keys(byTemp).map((k:any)=>({t:Number(k),s:byTemp[Number(k)]}));
      arr.sort((a:any,b:any)=>a.t-b.t);
      return arr.length?arr:[{t:50,s:20},{t:95,s:100}];
    };
    const target=safeNum(cfg.target_fps,40);
    const minTdp=safeNum(cfg.min_tdp,15);
    const maxTdp=Math.min(80,safeNum(cfg.max_tdp,80));
    const initialTdp=safeNum(cfg.initial_tdp,35);

    // --- сводка
    const goal = m.effective_target_fps!=null ? safeNum(m.effective_target_fps,0) : target+2;
    const fps = m.last_fps!=null ? safeNum(m.last_fps,0) : null;
    const tdpNow = t.current_tdp!=null ? safeNum(t.current_tdp,0) : null;
    const temp = f.current_temperature!=null ? safeNum(f.current_temperature,0) : null;
    const pwm = f.pwm_percent?.length && f.pwm_percent[0]!=null ? safeNum(f.pwm_percent[0],0) : null;
    const rpm = f.fan_rpm?.length && f.fan_rpm[0]!=null ? f.fan_rpm[0] : null;
    const phase = !enabled ? 'off' : (m.phase || (m.state==='waiting' ? 'waiting' : 'holding'));
    const fpsColor = fps==null || !enabled ? undefined : fps >= goal-2 ? COLORS.ok : fps >= goal-6 ? COLORS.warn : COLORS.bad;
    const noFps = enabled && (phase==='waiting' || fps==null);

    // --- игра и экран одной строкой
    const displayText = (()=>{
      const d=String(m.display||''); const i=d.indexOf('-');
      if(i<0) return '';
      const res=d.slice(i+1).replace('x','×');
      return d.slice(0,i)==='handheld' ? tr('display.handheld',res) : tr('display.external',res);
    })();
    const levels = m.game_levels && m.game_levels.length
      ? Array.from(new Set(m.game_levels.slice(-8).map((v:any)=>Math.round(Number(v))))).sort((a:any,b:any)=>a-b).join(' / ')
      : '';
    const gameLine = [
      m.game && m.game!=='default' ? (m.game_name || m.game) : tr('game.unknown'),
      displayText,
      levels ? tr('game.levels', levels) : '',
    ].filter(Boolean).join(' · ');

    const errors: string[] = [];
    if (error) errors.push(error);
    (stats&&stats.init_errors||[]).forEach((e:any)=>errors.push(`${tr('init.title')}: ${String(e)}`));

    const language = cfg.language==='en'||cfg.language==='ru' ? cfg.language : 'auto';
    const setLanguage = async (lang:string) => {
      setCfg((x:any)=>({...x,language:lang}));
      const ok=await rpc('set_language',{language:lang});
      if (!ok) setError(tr('err.lang'));
      await refresh();
    };
    const languageRow = (
      <PanelSectionRow>
        <DropdownItem label={tr('lang.title')} selectedOption={language}
          rgOptions={[{data:'auto',label:tr('lang.auto')},{data:'en',label:tr('lang.en')},{data:'ru',label:tr('lang.ru')}]}
          onChange={(o:any)=>setLanguage(o.data)}/>
      </PanelSectionRow>
    );

    return <>
      <PanelSection>
        {errors.map((e,i)=><PanelSectionRow key={`e${i}`}><Banner text={e}/></PanelSectionRow>)}
        <PanelSectionRow>
          <ToggleField label={tr('toggle.plugin')} checked={pluginEnabled} onChange={togglePlugin}
            description={!pluginEnabled ? tr('toggle.plugin.off') : guiPid ? tr('toggle.plugin.gui') : tr('toggle.plugin.on')}/>
        </PanelSectionRow>
        {pluginActive && <>
          <PanelSectionRow>
            <ToggleField label={tr('toggle.autotdp')} checked={enabled} onChange={toggleAuto}
              description={enabled ? tr('toggle.autotdp.on') : tr('toggle.autotdp.off')}/>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{width:'100%'}}>
              <Tiles tiles={[
                {label:tr('sum.fps'), value: fps!=null ? fps.toFixed(0) : '—', sub: enabled ? tr('sum.goal', goal) : '', color: fpsColor},
                {label:tr('sum.tdp'), value: tdpNow!=null ? tdpNow.toFixed(0) : '—', sub: W},
                {label:tr('sum.temp'), value: temp!=null ? temp.toFixed(0) : '—', sub: '°C'},
              ]}/>
              <StatusLine text={tr('phase.'+phase)} tone={PHASE_TONE[phase] || 'dim'}/>
              {enabled && <HistoryChart history={m.history||[]} goal={goal} maxTdp={maxTdp} legend={tr('chart.legend')} unitW={W}/>}
              <div style={{fontSize:12,color:COLORS.dim,marginTop:6}}>{gameLine}</div>
            </div>
          </PanelSectionRow>
          {noFps && <PanelSectionRow><Banner tone="warn" text={tr('warn.noFps')}/></PanelSectionRow>}
          <PanelSectionRow>
            <SliderField label={tr('slider.targetFps')} value={target} min={30} max={120} step={5} showValue onChange={(v:number)=>updateMonitorParam('target_fps',v)}/>
          </PanelSectionRow>
          <FoldHeader title={tr('fold.limits', minTdp, maxTdp)} open={limitsOpen} onToggle={toggleLimits}/>
          {limitsOpen && <>
            <PanelSectionRow><SliderField label={tr('slider.minTdp')} value={minTdp} min={5} max={maxTdp} step={1} showValue valueSuffix={` ${W}`} onChange={(v:number)=>updateMonitorParam('min_tdp',v)}/></PanelSectionRow>
            <PanelSectionRow><SliderField label={tr('slider.maxTdp')} value={maxTdp} min={minTdp} max={80} step={1} showValue valueSuffix={` ${W}`} onChange={(v:number)=>updateMonitorParam('max_tdp',v)}/></PanelSectionRow>
            <PanelSectionRow><SliderField label={tr('slider.startTdp')} description={enabled?tr('slider.startTdp.on'):tr('slider.startTdp.off')} value={initialTdp} min={5} max={80} step={1} showValue valueSuffix={` ${W}`} onChange={async(v:number)=>{const ok=await save('initial_tdp',v);if(ok && !enabled) await rpc('set_tdp',{value:v});}}/></PanelSectionRow>
          </>}
        </>}
      </PanelSection>

      {pluginActive && <PanelSection title={tr('section.fan')}>
        {!f.available && <PanelSectionRow><span style={{color:COLORS.dim,fontSize:13}}>{tr('fan.notDetected')}</span></PanelSectionRow>}
        {f.available && <>
          <PanelSectionRow>
            <ToggleField label={tr('fan.control')} checked={!!cfg.fan_control?.enabled}
              description={cfg.fan_control?.enabled?tr('fan.control.on'):tr('fan.control.off')}
              onChange={async(v:boolean)=>{const ok=await rpc(v?'enable_fan_control':'disable_fan_control');if(ok) await refresh();}}/>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{width:'100%'}}>
              <CurveGraph points={curveFromConfig(cfg)} height={140} now={{t: temp, s: pwm}}/>
              <div style={{fontSize:12,color:COLORS.tdp,textAlign:'right',marginTop:2}}>
                {tr('fan.caption', temp!=null?temp.toFixed(0):'—', pwm!=null?pwm.toFixed(0):'—', rpm!=null?rpm:'—')}
              </div>
            </div>
          </PanelSectionRow>
          <PanelSectionRow><ButtonItem layout="below" onClick={()=>{
            const lang=cfg.language;
            setCurveMsg('');
            showModal(<FanCurveModal initial={curveFromConfig(cfg)} tr={(k:string,...a:Array<string|number>)=>translate(lang,k,...a)}
              now={{t: temp, s: null}}
              onSave={async(pts:CurvePoint[])=>{
                const obj:any={};
                pts.forEach(p=>{obj[String(Math.round(p.t))]=Math.round(p.s);});
                const res=await rpc('set_fan_curve',{curve:obj});
                if (res && res.ok) { setCurveMsg(tr('curve.saved')); await refresh(); return {ok:true}; }
                return {ok:false, error:(res&&res.error)||tr('search.unknown')};
              }}/>);
          }}>{tr('curve.edit')}</ButtonItem></PanelSectionRow>
          {curveMsg && <PanelSectionRow><span style={{color:COLORS.ok,fontSize:12}}>{curveMsg}</span></PanelSectionRow>}
        </>}
      </PanelSection>}

      <PanelSection>
        <FoldHeader title={tr('fold.advanced')} open={advOpen} onToggle={toggleAdv}/>
        {advOpen && <>
          {pluginActive && <>
            <PanelSectionRow><ToggleField label={tr('toggle.loadBoost')} description={cfg.load_boost_enabled?tr('toggle.loadBoost.on', safeNum(cfg.load_boost_threshold,95)):tr('toggle.loadBoost.off')} checked={!!cfg.load_boost_enabled} onChange={async(v:boolean)=>{const ok=await save('load_boost_enabled',v);if(ok) await refresh();}}/></PanelSectionRow>
            {cfg.load_boost_enabled && <PanelSectionRow><SliderField label={tr('slider.threshold')} value={safeNum(cfg.load_boost_threshold,95)} min={90} max={100} step={1} showValue valueSuffix="%" onChange={(v:number)=>save('load_boost_threshold',v)}/></PanelSectionRow>}
            <PanelSectionRow><SliderField label={tr('slider.interval')} description={tr('slider.interval.desc')} value={safeNum(cfg.check_interval_sec,1)} min={0.5} max={5} step={0.5} showValue valueSuffix=" s" onChange={async(v:number)=>{setCfg((x:any)=>({...x,check_interval_sec:v})); const ok=await rpc('set_check_interval',{seconds:v}); if(!ok) setError(tr('err.save'));}}/></PanelSectionRow>
            <PanelSectionRow><ToggleField label={tr('src.hud')} description={cfg.mangohud_display?tr('src.hud.on'):tr('src.hud.off')} checked={!!cfg.mangohud_display} onChange={async(v:boolean)=>{const ok=await rpc('set_mangohud_display',{enabled:v});if(ok) await refresh();}}/></PanelSectionRow>
          </>}
          {languageRow}
        </>}
        <FoldHeader title={tr('fold.diag')} open={diagOpen} onToggle={toggleDiag}/>
        {diagOpen && <PanelSectionRow>
          <div style={{width:'100%'}}>
            <InfoRow label={tr('row.build')} value={(stats&&stats.build) || tr('row.build.old')}/>
            <InfoRow label={tr('row.tdpBackend')} value={t.backend || 'none'}/>
            <InfoRow label={tr('row.tdpSource')} value={t.tdp_source==='setpoint' ? tr('row.tdpSource.setpoint') : t.tdp_source}/>
            <InfoRow label={tr('row.controller')} value={m.state || tr('row.controller.stopped')}/>
            <InfoRow label={tr('row.tdpDecision')} value={m.tdp_hold_level!=null ? tr('row.tdpCapped', m.tdp_hold_level) : m.tdp_decision}/>
            <InfoRow label={tr('search.state')} value={tr('search.state.'+((m.tdp_search&&m.tdp_search.state)||'idle'))}/>
            <InfoRow label={tr('search.good')} value={(m.tdp_search&&m.tdp_search.good_w)!=null?`${m.tdp_search.good_w} ${W}`:null}/>
            <InfoRow label={tr('search.bad')} value={(m.tdp_search&&m.tdp_search.bad_w)!=null?`${m.tdp_search.bad_w} ${W}`:null}/>
            <InfoRow label={tr('search.probes')} value={(m.tdp_search&&(m.tdp_search.last_search_probes||m.tdp_search.probes))||0}/>
            <InfoRow label={tr('row.cpuLoad')} value={m.last_cpu_load!=null ? `${safeNum(m.last_cpu_load,0).toFixed(0)}%` : null}/>
            <InfoRow label={tr('row.gpuLoad')} value={m.last_gpu_load!=null ? `${safeNum(m.last_gpu_load,0).toFixed(0)}%` : null}/>
            <InfoRow label={tr('src.source')} value={m.fps_source ? String(m.fps_source).split('/').pop() : tr('src.sourceDefault')}/>
            <InfoRow label={tr('fan.controller')} value={f.available ? tr('fan.controller.ok', f.channels || 0) : tr('fan.controller.none')}/>
          </div>
        </PanelSectionRow>}
      </PanelSection>
    </>;
  };
}

// Иконка плагина: микросхема с молнией (управление мощностью чипа).
// Цвет — currentColor, поэтому значок подсвечивается вместе с остальными в меню Decky.
// Тот же рисунок лежит в assets/icon.svg.
const PluginIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="1em" height="1em" fill="none"
    stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <rect x="4.5" y="4.5" width="15" height="15" rx="2.8"/>
    <path d="M9.5 1.8v2.7M14.5 1.8v2.7M9.5 19.5v2.7M14.5 19.5v2.7M1.8 9.5h2.7M1.8 14.5h2.7M19.5 9.5h2.7M19.5 14.5h2.7"/>
    <path d="M13.7 6.6 8.3 13h3.6l-1.6 4.4L15.7 11h-3.6z" fill="currentColor" stroke="none"/>
  </svg>
);

export default function createPlugin(serverAPI: ServerAPI) {
  const Content=makeContent(serverAPI);
  return {
    title:<div className={staticClasses?.Title || ''}>GPD5CachyAutoTDP</div>,
    content:<Content/>,
    icon:<PluginIcon/>,
    onDismount(){}
  };
}
