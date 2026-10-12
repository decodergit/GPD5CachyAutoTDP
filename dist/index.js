// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
(function (React, DFL) {
  'use strict';
  var h = React.createElement;
  var useEffect = React.useEffect;
  var useState = React.useState;
  var useRef = React.useRef;
  var PanelSection = DFL && DFL.PanelSection;
  var PanelSectionRow = DFL && DFL.PanelSectionRow;
  var SliderField = DFL && DFL.SliderField;
  var ToggleField = DFL && DFL.ToggleField;
  var ButtonItem = DFL && DFL.ButtonItem;
  var staticClasses = DFL && DFL.staticClasses;

  var DEFAULT_CONFIG = {enabled:false,target_fps:40,min_tdp:15,max_tdp:80,initial_tdp:35,load_boost_enabled:true,load_boost_threshold:95,mangohud_display:false,check_interval_sec:3,hysteresis_threshold:5,fan_control:{enabled:true}};
function looksLikeConfig(o){var keys=['enabled','target_fps','min_tdp','max_tdp','initial_tdp','fan_control'];var n=0;for(var i=0;i<keys.length;i++){if(Object.prototype.hasOwnProperty.call(o,keys[i]))n++;}return n>=2;}
  function unwrap(v){
    var value=v;
    for(var depth=0;depth<4;depth++){
      if(typeof value==='string'){try{value=JSON.parse(value);}catch(e){return value;}continue;}
      if(!value||typeof value!=='object'||Array.isArray(value))return value;
      if(value.success===false){return {__error:typeof value.result==='string'?value.result:JSON.stringify(value.result)};}
      if(looksLikeConfig(value))return value;
      if(Object.prototype.hasOwnProperty.call(value,'result')){value=value.result;continue;}
      if(Object.prototype.hasOwnProperty.call(value,'data')){value=value.data;continue;}
      return value;
    }
    return value;
  }
  function describe(v){return v===undefined?'undefined':v===null?'null':typeof v==='string'?v:JSON.stringify(v);}
  function num(v,f){ var n=Number(v); return Number.isFinite(n)?n:f; }
  function Row(props){
    return h(PanelSectionRow,null,h('div',{style:{display:'flex',justifyContent:'space-between',width:'100%',gap:12}},h('span',null,props.label),h('span',{style:{fontFamily:'monospace'}},props.value==null?'—':String(props.value))));
  }
  function makeContent(serverAPI){
    async function rpc(method,args){
      try{var raw=await serverAPI.callPluginMethod(method,args||{});var result=unwrap(raw);console.log('[AutoTDP] RPC',method,result);return result;}
      catch(e){console.error('[AutoTDP] RPC '+method,e);return null;}
    }
    function Content(){
      var s1=useState(null),cfg=s1[0],setCfg=s1[1];
      var s2=useState(null),stats=s2[0],setStats=s2[1];
      var coresDraftState=useState(null), coresDraft=coresDraftState[0], setCoresDraft=coresDraftState[1];
      var s3=useState(''),error=s3[0],setError=s3[1];
      var pendingTimers=useRef({});
      var refreshBlockedUntil=useRef(0);
      async function refresh(){
        if(Date.now()<refreshBlockedUntil.current)return;
        var c=await rpc('get_config',{});
        if(c && c.__error){setError('Backend RPC get_config вернул неверный ответ: '+c.__error);return;}
        if(c && typeof c==='object' && !Array.isArray(c)){
          setError(c._backend_error?'AutoTDP backend: '+c._backend_error:'');
          setCfg(Object.assign({},DEFAULT_CONFIG,c,{fan_control:Object.assign({},DEFAULT_CONFIG.fan_control,c.fan_control||{})}));
        } else {setError('Backend RPC get_config вернул неверный ответ: '+describe(c));return;}
        var st=await rpc('get_stats',{});
        if(st && typeof st==='object') setStats(st); else setError('Backend RPC get_stats не отвечает');
      }
      useEffect(function(){refresh();var timer=setInterval(refresh,2000);return function(){clearInterval(timer);};},[]);
      if(!cfg) return h(PanelSection,{title:'Auto TDP / FPS'},h(PanelSectionRow,null,h('span',null,error||'Подключение к backend…')));
      async function save(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var ok=await rpc('set_config_value',{key:key,value:value});if(!ok)setError('Backend не принял изменение');return ok;} function updateMonitorParam(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var oldTimer=pendingTimers.current[key];if(oldTimer)clearTimeout(oldTimer);refreshBlockedUntil.current=Date.now()+700;pendingTimers.current[key]=setTimeout(async function(){var args={};if(key==='min_tdp')args.min_tdp=num(value,15);else if(key==='max_tdp')args.max_tdp=num(value,80);else if(key==='target_fps')args.target_fps=num(value,40);else {await save(key,value);return;}var ok=await rpc('update_monitor_params',args);if(!ok)setError('Backend не принял параметры AutoTDP');refreshBlockedUntil.current=Date.now()+500;},250);}
      var enabled=!!cfg.enabled;
      async function toggle(value){
        var ok=value?await rpc('start_monitor',{min_tdp:num(cfg.min_tdp,15),max_tdp:num(cfg.max_tdp,80),target_fps:num(cfg.target_fps,40),enable_auto:true}):await rpc('stop_monitor');
        if(!ok){setError('Не удалось изменить состояние AutoTDP');return;} await save('enabled',value); await refresh();
      }
      var t=(stats&&stats.tdp)||{},m=(stats&&stats.monitor)||{},f=(stats&&stats.fan)||{};
      var cores=Object.assign({available:false,min_cores:2,max_cores:0,active_cores:0,online_threads:0,total_threads:0},(stats&&stats.cores)||{});
      var coresStatusText=function(op,draft){
        if(!op) return '';
        if(op.state==='running') return 'Изменение ядер: '+(op.stage||'выполняется')+(op.detail?' — '+op.detail:'')+'…';
        if(op.state==='done') return 'Готово: активно '+(op.result&&op.result.applied)+' физ. ядер';
        if(op.state==='error') return 'Не выполнено: '+((op.result&&op.result.error)||'неизвестная ошибка');
        return draft!=null ? 'Запрошено '+draft+' ядер' : '';
      };
      var target=num(cfg.target_fps,40),minTdp=num(cfg.min_tdp,15),maxTdp=Math.min(80,num(cfg.max_tdp,80)),initialTdp=num(cfg.initial_tdp,35);
      return h(React.Fragment,null,
        h(PanelSection,{title:'Auto TDP'},h(PanelSectionRow,null,h(ToggleField,{label:'Auto TDP',description:enabled?'Running':'Stopped',checked:enabled,onChange:toggle}))),
        error&&h(PanelSection,{title:'Status'},h(PanelSectionRow,null,h('span',{style:{color:'#ffb3b3'}},error))),
        h(PanelSection,{title:'Auto TDP / FPS'},
          h(Row,{label:'Build',value:(stats&&stats.build)||'старый backend: переустановите архив'}),
          h(Row,{label:'TDP backend',value:t.backend||'none'}),
          h(Row,{label:'Current TDP',value:t.current_tdp!=null?num(t.current_tdp,0).toFixed(1)+' W':'—'}),
          h(Row,{label:'TDP source',value:t.tdp_source==='setpoint'?'setpoint (ryzenadj readback unavailable)':(t.tdp_source||'—')}),
          h(Row,{label:'Average FPS',value:m.last_fps!=null?num(m.last_fps,0).toFixed(1):'—'}),
          h(Row,{label:'Effective FPS goal',value:m.effective_target_fps!=null?String(m.effective_target_fps):'—'}),
          h(Row,{label:'TDP decision',value:m.tdp_hold_level!=null?'capped at '+m.tdp_hold_level+' W':(m.tdp_decision||'—')}),
          h(Row,{label:'Core evacuation',value:cores.evacuation?(cores.evacuation.ok?'ok, '+(cores.evacuation.moved_threads||0)+' threads moved':'blocked: '+(cores.evacuation_stuck||0)+' threads stuck'):'—'}),
          h(Row,{label:'CPU load',value:m.last_cpu_load!=null?num(m.last_cpu_load,0).toFixed(1)+'%':'—'}),
          h(Row,{label:'GPU load',value:m.last_gpu_load!=null?num(m.last_gpu_load,0).toFixed(1)+'%':'—'}),
          h(Row,{label:'Controller',value:m.state||'stopped'}),
          h(PanelSectionRow,null,h(SliderField,{label:'Target FPS',value:target,min:30,max:120,step:5,showValue:true,onChange:function(v){updateMonitorParam('target_fps',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Start TDP',description:enabled?'Used when Auto TDP starts':'Applied when Auto TDP is switched off',value:initialTdp,min:5,max:80,step:1,showValue:true,valueSuffix:' W',onChange:async function(v){var ok=await save('initial_tdp',v);if(ok&&!enabled)await rpc('set_tdp',{value:v});}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Minimum TDP',value:minTdp,min:5,max:maxTdp,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('min_tdp',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Maximum TDP',value:maxTdp,min:minTdp,max:80,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('max_tdp',v);}})),
          cores.available&&h(React.Fragment,null,h(PanelSectionRow,null,h(SliderField,{label:'Active CPU cores',description:'Physical cores with SMT kept together; '+cores.online_threads+'/'+cores.total_threads+' threads online',value:coresDraft!=null?coresDraft:cores.active_cores,min:cores.min_cores,max:cores.max_cores,step:1,showValue:true,onChange:function(v){setCoresDraft(v);rpc('set_active_cores',{cores:v}).then(function(res){if(!res||res.started===false)setError('Не удалось начать изменение ядер: '+((res&&res.error)||'нет ответа backend'));else setCoresDraft(v);});}})),h(PanelSectionRow,null,h('span',{style:{color:'#dbeafe'}},coresStatusText(cores.operation,coresDraft)))),
          h(PanelSectionRow,null,h(ToggleField,{label:'High-load TDP boost',description:cfg.load_boost_enabled?'CPU >'+num(cfg.load_boost_threshold,95)+'% boosts TDP even when FPS is already on target; GPU >'+num(cfg.load_boost_threshold,95)+'% boosts only when FPS is below target':'Disabled',checked:!!cfg.load_boost_enabled,onChange:async function(v){var ok=await save('load_boost_enabled',v);if(ok)await refresh();}})),
          h(PanelSectionRow,null,h(SliderField,{label:'High-load threshold',value:num(cfg.load_boost_threshold,95),min:90,max:100,step:1,showValue:true,valueSuffix:'%',onChange:function(v){save('load_boost_threshold',v);}})),
        ),
        h(PanelSection,{title:'Fan curve'},
          h(Row,{label:'Controller',value:f.available?'gpdfan / PWM':'not detected'}),
          h(Row,{label:'Temperature',value:f.current_temperature!=null?num(f.current_temperature,0).toFixed(1)+' °C':'—'}),
          h(Row,{label:'Channels',value:f.channels||0}),
          h(Row,{label:'Fan RPM',value:f.fan_rpm&&f.fan_rpm.length?f.fan_rpm.map(function(v){return v==null?'—':v}).join(', '):'—'}),
          h(Row,{label:'PWM',value:f.pwm_percent&&f.pwm_percent.length?f.pwm_percent.map(function(v){return v==null?'—':v.toFixed(1)+'%'}).join(', '):'—'}),
          h(PanelSectionRow,null,h(ToggleField,{label:'Fan control',description:(cfg.fan_control&&cfg.fan_control.enabled)?'Curve enabled':'Curve disabled',checked:!!(cfg.fan_control&&cfg.fan_control.enabled),disabled:!f.available,onChange:async function(v){var ok=await rpc(v?'enable_fan_control':'disable_fan_control');if(ok)await refresh();}})),
          !f.available&&h(PanelSectionRow,null,h('span',{style:{color:'#94a3b8'}},'PWM fan controller not detected.'))
        ),
        h(PanelSection,{title:'FPS source / requirements'},h(PanelSectionRow,null,h('span',{style:{color:'#dbeafe'}},'Keep system MangoHud enabled. For correct AutoTDP behavior, disable FPS limits both in the game and in the system/gamescope. The plugin needs uncapped FPS to see the real performance headroom.')),h(Row,{label:'Source',value:m.fps_source||'MangoHud / mangoapp CSV'}),h(PanelSectionRow,null,h(ToggleField,{label:'MangoHud display',description:cfg.mangohud_display?'HUD visible':'HUD hidden (logging remains active)',checked:!!cfg.mangohud_display,onChange:async function(v){var ok=await rpc('set_mangohud_display',{enabled:v});if(ok)await refresh();}})))
      );
    }
    return {title:h('div',{className:staticClasses&&staticClasses.Title||''},'GPD5CachyAutoTDP'),content:h(Content),icon:h('span',null,'⚡'),onDismount:function(){}};
  }
  return makeContent;
})(SP_REACT, DFL)
