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

  var I18N={en: {'section.autotdp':'Auto TDP','section.fps':'Auto TDP / FPS','section.status':'Status','section.fan':'Fan curve','section.source':'FPS source / requirements','toggle.autotdp':'Auto TDP','toggle.running':'Running','toggle.stopped':'Stopped','row.build':'Build','row.build.old':'old backend: reinstall the archive','row.tdpBackend':'TDP backend','row.currentTdp':'Current TDP','row.tdpSource':'TDP source','row.tdpSource.setpoint':'setpoint (ryzenadj readback unavailable)','row.avgFps':'Average FPS','row.effectiveGoal':'Effective FPS goal','row.tdpDecision':'TDP decision','row.tdpCapped':'capped at {0} W','row.cpuLoad':'CPU load','row.gpuLoad':'GPU load','row.controller':'Controller','row.controller.stopped':'stopped','slider.targetFps':'Target FPS','slider.startTdp':'Start TDP','slider.startTdp.on':'Used when Auto TDP starts','slider.startTdp.off':'Applied when Auto TDP is switched off','slider.minTdp':'Minimum TDP','slider.maxTdp':'Maximum TDP','slider.threshold':'High-load threshold','toggle.loadBoost':'High-load TDP boost','toggle.loadBoost.on':'CPU >{0}% boosts TDP even when FPS is already on target; GPU >{0}% boosts only when FPS is below target','toggle.loadBoost.off':'Disabled','fan.controller':'Controller','fan.controller.ok':'gpdfan / PWM','fan.controller.none':'not detected','fan.temp':'Temperature','fan.channels':'Channels','fan.rpm':'Fan RPM','fan.pwm':'PWM','fan.control':'Fan control','fan.control.on':'Curve enabled','fan.control.off':'Curve disabled','fan.notDetected':'PWM fan controller not detected.','src.note':'Keep system MangoHud enabled. For correct AutoTDP behavior, disable FPS limits both in the game and in the system/gamescope. The plugin needs uncapped FPS to see the real performance headroom.','src.source':'Source','src.sourceDefault':'MangoHud / mangoapp CSV','src.hud':'MangoHud display','src.hud.on':'HUD visible','src.hud.off':'HUD hidden (logging remains active)','lang.title':'Language','lang.en':'English','lang.ru':'Русский','status.connecting':'Connecting to backend…','err.getConfig':'Backend RPC get_config returned an invalid response: {0}','err.getStats':'Backend RPC get_stats does not respond','err.backend':'AutoTDP backend: {0}','err.save':'Backend did not accept the change','err.params':'Backend did not accept AutoTDP parameters','err.toggle':'Could not change AutoTDP state','err.lang':'Could not save the language'},ru: {'section.autotdp':'Auto TDP','section.fps':'Auto TDP / FPS','section.status':'Статус','section.fan':'Кривая вентилятора','section.source':'Источник FPS / требования','toggle.autotdp':'Auto TDP','toggle.running':'Работает','toggle.stopped':'Остановлен','row.build':'Сборка','row.build.old':'старый backend: переустановите архив','row.tdpBackend':'Бэкенд TDP','row.currentTdp':'Текущий TDP','row.tdpSource':'Источник TDP','row.tdpSource.setpoint':'заданное значение (чтение ryzenadj недоступно)','row.avgFps':'Средний FPS','row.effectiveGoal':'Эффективная цель FPS','row.tdpDecision':'Решение по TDP','row.tdpCapped':'ограничено {0} Вт','row.cpuLoad':'Загрузка CPU','row.gpuLoad':'Загрузка GPU','row.controller':'Контроллер','row.controller.stopped':'остановлен','slider.targetFps':'Целевой FPS','slider.startTdp':'Стартовый TDP','slider.startTdp.on':'Используется при запуске Auto TDP','slider.startTdp.off':'Применяется при выключении Auto TDP','slider.minTdp':'Минимальный TDP','slider.maxTdp':'Максимальный TDP','slider.threshold':'Порог высокой нагрузки','toggle.loadBoost':'Повышение TDP при высокой нагрузке','toggle.loadBoost.on':'CPU >{0}% повышает TDP даже когда FPS уже на цели; GPU >{0}% повышает только когда FPS ниже цели','toggle.loadBoost.off':'Выключено','fan.controller':'Контроллер','fan.controller.ok':'gpdfan / PWM','fan.controller.none':'не обнаружен','fan.temp':'Температура','fan.channels':'Каналы','fan.rpm':'Обороты вентилятора','fan.pwm':'PWM','fan.control':'Управление вентилятором','fan.control.on':'Кривая включена','fan.control.off':'Кривая выключена','fan.notDetected':'Контроллер PWM-вентилятора не обнаружен.','src.note':'Оставьте системный MangoHud включённым. Для корректной работы Auto TDP отключите ограничение FPS и в игре, и в системе/gamescope. Плагину нужен неограниченный FPS, чтобы видеть реальный запас производительности.','src.source':'Источник','src.sourceDefault':'MangoHud / CSV mangoapp','src.hud':'Отображение MangoHud','src.hud.on':'HUD виден','src.hud.off':'HUD скрыт (запись в лог продолжается)','lang.title':'Язык','lang.en':'English','lang.ru':'Русский','status.connecting':'Подключение к backend…','err.getConfig':'Backend RPC get_config вернул неверный ответ: {0}','err.getStats':'Backend RPC get_stats не отвечает','err.backend':'AutoTDP backend: {0}','err.save':'Backend не принял изменение','err.params':'Backend не принял параметры AutoTDP','err.toggle':'Не удалось изменить состояние AutoTDP','err.lang':'Не удалось сохранить язык'}};
    function tr(lang,key){
      var l=lang==='ru'?'ru':'en';
      var args=Array.prototype.slice.call(arguments,2);
      var s=I18N[l][key]; if(s===undefined) s=I18N.en[key]; if(s===undefined) s=key;
      return s.replace(/\{(\d+)\}/g,function(_,i){return args[Number(i)]!==undefined?String(args[Number(i)]):'';});
    }
  var DEFAULT_CONFIG = {enabled:false,target_fps:40,min_tdp:15,max_tdp:80,initial_tdp:35,load_boost_enabled:true,load_boost_threshold:95,mangohud_display:false,language:'en',check_interval_sec:3,hysteresis_threshold:5,fan_control:{enabled:true}};
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
  function cfgLang(c){return c&&c.language==='ru'?'ru':'en';}
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
      var s3=useState(''),error=s3[0],setError=s3[1];
      var pendingTimers=useRef({});
      var refreshBlockedUntil=useRef(0);
      async function refresh(){
        if(Date.now()<refreshBlockedUntil.current)return;
        var c=await rpc('get_config',{});
        if(c && c.__error){setError(tr(cfgLang(cfg),'err.getConfig',c.__error));return;}
        if(c && typeof c==='object' && !Array.isArray(c)){
          setError(c._backend_error?tr(c.language,'err.backend',c._backend_error):'');
          setCfg(Object.assign({},DEFAULT_CONFIG,c,{fan_control:Object.assign({},DEFAULT_CONFIG.fan_control,c.fan_control||{})}));
        } else {setError(tr(cfgLang(cfg),'err.getConfig',describe(c)));return;}
        var st=await rpc('get_stats',{});
        if(st && typeof st==='object') setStats(st); else setError(tr(cfgLang(cfg),'err.getStats'));
      }
      useEffect(function(){refresh();var timer=setInterval(refresh,2000);return function(){clearInterval(timer);};},[]);
      if(!cfg) return h(PanelSection,{title:tr(cfgLang(cfg),'section.fps')},h(PanelSectionRow,null,h('span',null,error||tr(cfgLang(cfg),'status.connecting'))));
      async function save(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var ok=await rpc('set_config_value',{key:key,value:value});if(!ok)setError(tr(cfgLang(cfg),'err.save'));return ok;} function updateMonitorParam(key,value){setCfg(function(x){return Object.assign({},x,{[key]:value});});var oldTimer=pendingTimers.current[key];if(oldTimer)clearTimeout(oldTimer);refreshBlockedUntil.current=Date.now()+700;pendingTimers.current[key]=setTimeout(async function(){var args={};if(key==='min_tdp')args.min_tdp=num(value,15);else if(key==='max_tdp')args.max_tdp=num(value,80);else if(key==='target_fps')args.target_fps=num(value,40);else {await save(key,value);return;}var ok=await rpc('update_monitor_params',args);if(!ok)setError(tr(cfgLang(cfg),'err.params'));refreshBlockedUntil.current=Date.now()+500;},250);}
      var enabled=!!cfg.enabled;
      async function toggle(value){
        var ok=value?await rpc('start_monitor',{min_tdp:num(cfg.min_tdp,15),max_tdp:num(cfg.max_tdp,80),target_fps:num(cfg.target_fps,40),enable_auto:true}):await rpc('stop_monitor');
        if(!ok){setError(tr(cfgLang(cfg),'err.toggle'));return;} await save('enabled',value); await refresh();
      }
      var t=(stats&&stats.tdp)||{},m=(stats&&stats.monitor)||{},f=(stats&&stats.fan)||{};
      var target=num(cfg.target_fps,40),minTdp=num(cfg.min_tdp,15),maxTdp=Math.min(80,num(cfg.max_tdp,80)),initialTdp=num(cfg.initial_tdp,35);
      return h(React.Fragment,null,
        h(PanelSection,{title:tr(cfgLang(cfg),'section.autotdp')},h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'toggle.autotdp'),description:enabled?tr(cfgLang(cfg),'toggle.running'):tr(cfgLang(cfg),'toggle.stopped'),checked:enabled,onChange:toggle}))),
        error&&h(PanelSection,{title:tr(cfgLang(cfg),'section.status')},h(PanelSectionRow,null,h('span',{style:{color:'#ffb3b3'}},error))),
        h(PanelSection,{title:tr(cfgLang(cfg),'section.fps')},
          h(Row,{label:tr(cfgLang(cfg),'row.build'),value:(stats&&stats.build)||tr(cfgLang(cfg),'row.build.old')}),
          h(Row,{label:tr(cfgLang(cfg),'row.tdpBackend'),value:t.backend||'none'}),
          h(Row,{label:tr(cfgLang(cfg),'row.currentTdp'),value:t.current_tdp!=null?num(t.current_tdp,0).toFixed(1)+' W':'—'}),
          h(Row,{label:tr(cfgLang(cfg),'row.tdpSource'),value:t.tdp_source==='setpoint'?tr(cfgLang(cfg),'row.tdpSource.setpoint'):(t.tdp_source||'—')}),
          h(Row,{label:tr(cfgLang(cfg),'row.avgFps'),value:m.last_fps!=null?num(m.last_fps,0).toFixed(1):'—'}),
          h(Row,{label:tr(cfgLang(cfg),'row.effectiveGoal'),value:m.effective_target_fps!=null?String(m.effective_target_fps):'—'}),
          h(Row,{label:tr(cfgLang(cfg),'row.tdpDecision'),value:m.tdp_hold_level!=null?tr(cfgLang(cfg),'row.tdpCapped',m.tdp_hold_level):(m.tdp_decision||'—')}),
          h(Row,{label:tr(cfgLang(cfg),'row.cpuLoad'),value:m.last_cpu_load!=null?num(m.last_cpu_load,0).toFixed(1)+'%':'—'}),
          h(Row,{label:tr(cfgLang(cfg),'row.gpuLoad'),value:m.last_gpu_load!=null?num(m.last_gpu_load,0).toFixed(1)+'%':'—'}),
          h(Row,{label:tr(cfgLang(cfg),'row.controller'),value:m.state||tr(cfgLang(cfg),'row.controller.stopped')}),
          h(PanelSectionRow,null,h(SliderField,{label:tr(cfgLang(cfg),'slider.targetFps'),value:target,min:30,max:120,step:5,showValue:true,onChange:function(v){updateMonitorParam('target_fps',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:tr(cfgLang(cfg),'slider.startTdp'),description:enabled?tr(cfgLang(cfg),'slider.startTdp.on'):tr(cfgLang(cfg),'slider.startTdp.off'),value:initialTdp,min:5,max:80,step:1,showValue:true,valueSuffix:' W',onChange:async function(v){var ok=await save('initial_tdp',v);if(ok&&!enabled)await rpc('set_tdp',{value:v});}})),
          h(PanelSectionRow,null,h(SliderField,{label:tr(cfgLang(cfg),'slider.minTdp'),value:minTdp,min:5,max:maxTdp,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('min_tdp',v);}})),
          h(PanelSectionRow,null,h(SliderField,{label:tr(cfgLang(cfg),'slider.maxTdp'),value:maxTdp,min:minTdp,max:80,step:1,showValue:true,valueSuffix:' W',onChange:function(v){updateMonitorParam('max_tdp',v);}})),
          h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'toggle.loadBoost'),description:cfg.load_boost_enabled?tr(cfgLang(cfg),'toggle.loadBoost.on',num(cfg.load_boost_threshold,95)):tr(cfgLang(cfg),'toggle.loadBoost.off'),checked:!!cfg.load_boost_enabled,onChange:async function(v){var ok=await save('load_boost_enabled',v);if(ok)await refresh();}})),
          h(PanelSectionRow,null,h(SliderField,{label:tr(cfgLang(cfg),'slider.threshold'),value:num(cfg.load_boost_threshold,95),min:90,max:100,step:1,showValue:true,valueSuffix:'%',onChange:function(v){save('load_boost_threshold',v);}})),
        ),
        h(PanelSection,{title:tr(cfgLang(cfg),'section.fan')},
          h(Row,{label:tr(cfgLang(cfg),'fan.controller'),value:f.available?tr(cfgLang(cfg),'fan.controller.ok'):tr(cfgLang(cfg),'fan.controller.none')}),
          h(Row,{label:tr(cfgLang(cfg),'fan.temp'),value:f.current_temperature!=null?num(f.current_temperature,0).toFixed(1)+' °C':'—'}),
          h(Row,{label:tr(cfgLang(cfg),'fan.channels'),value:f.channels||0}),
          h(Row,{label:tr(cfgLang(cfg),'fan.rpm'),value:f.fan_rpm&&f.fan_rpm.length?f.fan_rpm.map(function(v){return v==null?'—':v}).join(', '):'—'}),
          h(Row,{label:tr(cfgLang(cfg),'fan.pwm'),value:f.pwm_percent&&f.pwm_percent.length?f.pwm_percent.map(function(v){return v==null?'—':v.toFixed(1)+'%'}).join(', '):'—'}),
          h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'fan.control'),description:(cfg.fan_control&&cfg.fan_control.enabled)?tr(cfgLang(cfg),'fan.control.on'):tr(cfgLang(cfg),'fan.control.off'),checked:!!(cfg.fan_control&&cfg.fan_control.enabled),disabled:!f.available,onChange:async function(v){var ok=await rpc(v?'enable_fan_control':'disable_fan_control');if(ok)await refresh();}})),
          !f.available&&h(PanelSectionRow,null,h('span',{style:{color:'#94a3b8'}},tr(cfgLang(cfg),'fan.notDetected')))
        ),
        h(PanelSection,{title:tr(cfgLang(cfg),'section.source')},h(PanelSectionRow,null,h('span',{style:{color:'#dbeafe'}},tr(cfgLang(cfg),'src.note'))),h(Row,{label:tr(cfgLang(cfg),'src.source'),value:m.fps_source||tr(cfgLang(cfg),'src.sourceDefault')}),h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'src.hud'),description:cfg.mangohud_display?tr(cfgLang(cfg),'src.hud.on'):tr(cfgLang(cfg),'src.hud.off'),checked:!!cfg.mangohud_display,onChange:async function(v){var ok=await rpc('set_mangohud_display',{enabled:v});if(ok)await refresh();}}))),
        h(PanelSection,{title:tr(cfgLang(cfg),'lang.title')},h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'lang.en'),description:cfg.language==='en'?'✓':'',checked:cfg.language==='en',onChange:async function(v){if(!v)return;var ok=await rpc('set_language',{language:'en'});if(ok)await refresh();else setError(tr(cfgLang(cfg),'err.lang'));}})),h(PanelSectionRow,null,h(ToggleField,{label:tr(cfgLang(cfg),'lang.ru'),description:cfg.language==='ru'?'✓':'',checked:cfg.language==='ru',onChange:async function(v){if(!v)return;var ok=await rpc('set_language',{language:'ru'});if(ok)await refresh();else setError(tr(cfgLang(cfg),'err.lang'));}})))
      );
    }
    return {title:h('div',{className:staticClasses&&staticClasses.Title||''},'GPD5CachyAutoTDP'),content:h(Content),icon:h('span',null,'⚡'),onDismount:function(){}};
  }
  return makeContent;
})(SP_REACT, DFL)
