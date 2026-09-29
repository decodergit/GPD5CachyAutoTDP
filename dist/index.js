// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
(function (React, DFL) {
  'use strict';
  var h = React.createElement;
  var useEffect = React.useEffect;
  var useState = React.useState;
  var PanelSection = DFL && DFL.PanelSection;
  var PanelSectionRow = DFL && DFL.PanelSectionRow;
  var SliderField = DFL && DFL.SliderField;
  var ToggleField = DFL && DFL.ToggleField;
  var ButtonItem = DFL && DFL.ButtonItem;
  var staticClasses = DFL && DFL.staticClasses;

  var DEFAULT_CONFIG = {enabled:false,target_fps:40,min_tdp:15,max_tdp:55,initial_tdp:35,mangohud_display:false,check_interval_sec:3,hysteresis_threshold:5,fan_control:{enabled:true}};
  function unwrap(v){
    if(v && typeof v==='object' && !Array.isArray(v)){
      if(Object.prototype.hasOwnProperty.call(v,'result') && (Object.prototype.hasOwnProperty.call(v,'success') || Object.keys(v).length<=2)) return v.result;
      if(Object.prototype.hasOwnProperty.call(v,'data') && (Object.prototype.hasOwnProperty.call(v,'success') || Object.keys(v).length<=2)) return v.data;
    }
    return v;
  }
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
      var s3=useState(''),error=s3[0],setError=s3[1];
      async function refresh(){
        var c=await rpc('get_config',{});
        if(c && typeof c==='object' && !Array.isArray(c)) setCfg(Object.assign({},DEFAULT_CONFIG,c,{fan_control:Object.assign({},DEFAULT_CONFIG.fan_control,c.fan_control||{})}));
        else {setError('Backend RPC get_config вернул неверный ответ');return;}
        var st=await rpc('get_stats',{});
        if(st && typeof st==='object') setStats(st); else setError('Backend RPC get_stats не отвечает');
      }
      useEffect(function(){refresh();var timer=setInterval(refresh,2000);return function(){clearInterval(timer);};},[]);
      if(!cfg) return h(PanelSection,{title:'Auto TDP / FPS'},h(PanelSectionRow,null,h('span',null,error||'Подключение к backend…')));
      async function save(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var ok=await rpc('set_config_value',{key:key,value:value});if(!ok)setError('Backend не принял изменение');return ok;} async function updateMonitorParam(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var args={};if(key==='min_tdp')args.min_tdp=num(value,15);else if(key==='max_tdp')args.max_tdp=num(value,55);else if(key==='target_fps')args.target_fps=num(value,40);else return save(key,value);var ok=await rpc('update_monitor_params',args);if(!ok)setError('Backend не принял параметры AutoTDP');return ok;}
      var enabled=!!cfg.enabled;
      async function toggle(value){
        var ok=value?await rpc('start_monitor',{min_tdp:num(cfg.min_tdp,15),max_tdp:num(cfg.max_tdp,55),target_fps:num(cfg.target_fps,40),enable_auto:true}):await rpc('stop_monitor');
        if(!ok){setError('Не удалось изменить состояние AutoTDP');return;} await save('enabled',value); await refresh();
      }
      var t=(stats&&stats.tdp)||{},m=(stats&&stats.monitor)||{},f=(stats&&stats.fan)||{};
      var target=num(cfg.target_fps,40),minTdp=num(cfg.min_tdp,15),maxTdp=num(cfg.max_tdp,55),initialTdp=num(cfg.initial_tdp,35);
      return h(React.Fragment,null,
        error&&h(PanelSection,{title:'Status'},h(PanelSectionRow,null,h('span',{style:{color:'#ffb3b3'}},error))),
        h(PanelSection,{title:'Auto TDP / FPS'},
          h(Row,{label:'TDP backend',value:t.backend||'none'}),
          h(Row,{label:'Current TDP',value:t.current_tdp!=null?num(t.current_tdp,0).toFixed(1)+' W':'—'}),
          h(Row,{label:'TDP source',value:t.tdp_source==='setpoint'?'setpoint (ryzenadj readback unavailable)':(t.tdp_source||'—')}),
          h(Row,{label:'Average FPS',value:m.last_fps!=null?num(m.last_fps,0).toFixed(1):'—'}),
          h(Row,{label:'Controller',value:m.state||'stopped'}),
          h(PanelSectionRow,null,h(ToggleField,{label:'Auto TDP',description:enabled?'Running':'Stopped',checked:enabled,onChange:toggle})),
          h(PanelSectionRow,null,h(SliderField,{label:'Target FPS',value:target,min:30,max:120,step:5,showValue:true,onChange:function(v){updateMonitorParam('target_fps',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Start TDP',description:'Used only when no previous AutoTDP setpoint exists',value:initialTdp,min:5,max:55,step:1,showValue:true,valueSuffix:' W',onChange:function(v){save('initial_tdp',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Minimum TDP',value:minTdp,min:5,max:maxTdp,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('min_tdp',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:'Maximum TDP',value:maxTdp,min:minTdp,max:55,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('max_tdp',v);}})),
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
        h(PanelSection,{title:'FPS source'},h(Row,{label:'Source',value:m.fps_source||'MangoHud / mangoapp CSV'}),h(PanelSectionRow,null,h(ToggleField,{label:'MangoHud display',description:cfg.mangohud_display?'HUD visible':'HUD hidden (logging remains active)',checked:!!cfg.mangohud_display,onChange:async function(v){var ok=await rpc('set_mangohud_display',{enabled:v});if(ok)await refresh();}})))
      );
    }
    return {title:h('div',{className:staticClasses&&staticClasses.Title||''},'GPD5CachyAutoTDP'),content:h(Content),icon:h('span',null,'⚡'),onDismount:function(){}};
  }
  return makeContent;
})(SP_REACT, DFL)
