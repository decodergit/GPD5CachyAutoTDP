# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import asyncio, functools, logging, os, sys, time
from pathlib import Path
_PLUGIN_DIR=os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path: sys.path.insert(0,_PLUGIN_DIR)
try:
 import decky as _decky
 SETTINGS_DIR=getattr(_decky, 'DECKY_PLUGIN_SETTINGS_DIR', os.environ.get('DECKY_PLUGIN_SETTINGS_DIR', '/tmp/autotdpfps'))
 LOG_DIR=getattr(_decky, 'DECKY_PLUGIN_LOG_DIR', os.environ.get('DECKY_PLUGIN_LOG_DIR', '/tmp'))
except ImportError:
 try:
  import decky_plugin as _decky
  SETTINGS_DIR=getattr(_decky, 'DECKY_PLUGIN_SETTINGS_DIR', os.environ.get('DECKY_PLUGIN_SETTINGS_DIR', '/tmp/autotdpfps'))
  LOG_DIR=getattr(_decky, 'DECKY_PLUGIN_LOG_DIR', os.environ.get('DECKY_PLUGIN_LOG_DIR', '/tmp'))
 except ImportError:
  SETTINGS_DIR=os.environ.get('DECKY_PLUGIN_SETTINGS_DIR','/tmp/autotdpfps'); LOG_DIR=os.environ.get('DECKY_PLUGIN_LOG_DIR','/tmp')
try:
 Path(LOG_DIR).mkdir(parents=True,exist_ok=True)
 _handlers=[logging.StreamHandler(), logging.FileHandler(Path(LOG_DIR)/'plugin.log')]
except Exception:
 _handlers=[logging.StreamHandler()]
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s',handlers=_handlers)
logger=logging.getLogger('autotdp')

def _vendor_ryzenadj():
 try:
  local=Path(_PLUGIN_DIR)/'bin'/'ryzenadj'
  if local.is_file() and os.access(local,os.X_OK):
   return str(local)
  candidates=[
   Path(os.environ.get('DECKY_HOME','/home/deck/homebrew'))/'plugins/PowerControl/bin/ryzenadj',
   Path('/home/deck/homebrew/plugins/PowerControl/bin/ryzenadj'),
  ]
  source=next((p for p in candidates if p.is_file() and os.access(p,os.X_OK)),None)
  if source is not None:
   local.parent.mkdir(parents=True,exist_ok=True)
   import shutil
   shutil.copy2(source,local)
   os.chmod(local,0o755)
   logger.info('AutoTDP: vendored ryzenadj from PowerControl: %s',source)
 except Exception as e:
  logger.warning('AutoTDP: could not vendor ryzenadj: %s',e)

_vendor_ryzenadj()
from backend.config_manager import ConfigManager, ConfigException
from backend.tdp_controller import TDPController, TDPControllerException
from backend.monitor import TDPMonitor, TDPMonitorException
from backend.fan_controller import FanController
from backend.mangohud_controller import MangoHudController
from backend.cpu_topology import CpuTopology
try:
 from backend.epp_controller import EPPController, EPPNotAvailableException
except Exception: EPPController=None

# ---------------------------------------------------------------------------
# Состояние плагина хранится в модульном объекте, а не в self.
# Причина (лог 1.3.0): Decky вызывал _main с классом Plugin вместо экземпляра,
# из-за чего self.cfg и self._startup_watchdog() ломались.
# Все функции ниже не зависят от того, чем является первый аргумент.
# ---------------------------------------------------------------------------
class _State: pass
S=_State()
S.cfg=None; S.tdp=None; S.fan=None; S.mangohud=None; S.epp=None
S.monitor=None; S.watchdog_task=None; S.topology=None

WATCHDOG_TIMEOUT_S=10.0
WATCHDOG_COOLDOWN_S=30.0

def _safe(default, label):
 """Декоратор: исключение RPC не уходит в Decky, а логируется и заменяется значением по умолчанию."""
 def deco(fn):
  @functools.wraps(fn)
  async def wrapper(*args, **kwargs):
   try:
    return await fn(*args, **kwargs)
   except asyncio.CancelledError:
    raise
   except Exception as e:
    logger.exception("AutoTDP: %s failed: %s", label, e)
    return default() if callable(default) else default
  return wrapper
 return deco

async def _stop_runtime():
 old_monitor=S.monitor
 if old_monitor:
  try: old_monitor.stop(reset_to_initial=False)
  except Exception: logger.exception("AutoTDP: monitor cleanup failed during restart")
 old_fan=S.fan
 if old_fan:
  try: old_fan.disable()
  except Exception: logger.exception("AutoTDP: fan cleanup failed during restart")
 for attr in ('monitor','fan','tdp','mangohud','epp','cfg'):
  setattr(S, attr, None)

async def _initialize():
 logger.info("AutoTDP: initialization start")
 ok=True
 try:
  S.cfg=ConfigManager(SETTINGS_DIR); S.cfg.load_config(); logger.info("AutoTDP: config ready")
 except Exception as e:
  ok=False; logger.exception("AutoTDP: config initialization failed: %s", e)
 try:
  S.tdp=TDPController(); logger.info("AutoTDP: TDP ready backend=%s", S.tdp.backend)
 except Exception as e:
  ok=False; logger.exception("AutoTDP: TDP initialization failed: %s", e)
 try:
  S.fan=FanController(); logger.info("AutoTDP: fan ready available=%s", S.fan.is_available())
 except Exception as e:
  ok=False; logger.exception("AutoTDP: fan initialization failed: %s", e)
 try:
  S.mangohud=MangoHudController(); logger.info("AutoTDP: MangoHud config=%s", S.mangohud.get_path())
  try: S.mangohud.set_display(bool(S.cfg.get_value("mangohud_display", False)))
  except Exception as e: logger.warning("MangoHud visibility setup failed: %s", e)
 except Exception as e:
  ok=False; logger.exception("AutoTDP: MangoHud initialization failed: %s", e)
 try:
  S.topology=CpuTopology()
  saved=S.cfg.get_value('active_cores',None) if S.cfg else None
  if S.topology.available and saved is not None:
   S.topology.apply(int(saved))
  logger.info("AutoTDP: CPU topology cores=%s active=%s", len(S.topology.cores), S.topology.active_cores)
  S.topology.on_applied=lambda n: S.cfg.set_value('active_cores',n) if S.cfg else None
 except Exception as e:
  ok=False; logger.exception("AutoTDP: CPU topology initialization failed: %s", e)
 S.epp=None
 if EPPController:
  try: S.epp=EPPController()
  except Exception as e: logger.info('EPP unavailable: %s', e)
 logger.info("AutoTDP: EPP stage complete")
 try:
  S.monitor=TDPMonitor(S.tdp,S.cfg,S.fan); logger.info("AutoTDP: monitor ready")
 except Exception as e:
  ok=False; logger.exception("AutoTDP: monitor initialization failed: %s", e)
 try:
  if S.cfg and S.fan:
   fc=S.cfg.get_value('fan_control',{})
   if fc.get('enabled',True) and S.fan.is_available():
    try:
     S.fan.set_curve(fc.get('curve',S.fan.get_current_curve())); S.fan.enable()
     logger.info("AutoTDP: fan curve enabled")
    except Exception as e: logger.exception("Fan initialization failed: %s", e)
 except Exception as e:
  logger.exception("AutoTDP: fan curve restore failed: %s", e)
 try:
  if S.cfg and S.monitor and S.cfg.get_value('enabled',False) and S.tdp and S.tdp.available():
   S.monitor.start(S.cfg.get_value('min_tdp',15),S.cfg.get_value('max_tdp',80),S.cfg.get_value('target_fps',40),S.cfg.get_value('initial_tdp',35))
   logger.info("AutoTDP: restored running state")
 except Exception as e: logger.exception("Saved AutoTDP start failed: %s", e)
 logger.info("AutoTDP: initialization complete ok=%s", ok)
 return ok

async def _reinitialize(reason='watchdog'):
 logger.warning("AutoTDP: restarting plugin initialization: %s", reason)
 try:
  await _stop_runtime()
 finally:
  await asyncio.sleep(0.5)
 return await _initialize()

async def _startup_watchdog():
 logger.info("AutoTDP: startup watchdog enabled (waiting timeout=%.0fs)", WATCHDOG_TIMEOUT_S)
 last_restart=0.0
 while True:
  await asyncio.sleep(2.0)
  try:
   monitor=S.monitor
   if not monitor:
    continue
   stats=monitor.get_stats()
   waiting_for=float(stats.get('waiting_seconds') or 0.0)
   if stats.get('state') == TDPMonitor.STATE_WAITING and waiting_for > WATCHDOG_TIMEOUT_S:
    now=time.monotonic()
    if now-last_restart < WATCHDOG_COOLDOWN_S:
     continue
    last_restart=now
    logger.warning("AutoTDP: monitor stuck in waiting for %.1fs; performing full reinitialization", waiting_for)
    await _reinitialize(f"monitor waiting for {waiting_for:.1f}s")
  except asyncio.CancelledError:
   raise
  except Exception:
   logger.exception("AutoTDP: startup watchdog error")

def _watchdog_done(task):
 if task.cancelled(): return
 exc=task.exception()
 if exc: logger.error("AutoTDP: watchdog task ended with error: %r", exc)

class Plugin:
 async def _main(self):
  logger.info("AutoTDP: _main start")
  S.watchdog_task=asyncio.create_task(_startup_watchdog())
  S.watchdog_task.add_done_callback(_watchdog_done)
  return await _initialize()

 async def _unload(self):
  try:
   task=S.watchdog_task
   if task:
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
   if S.monitor: S.monitor.stop()
   if S.fan: S.fan.disable()
  except Exception: logger.exception("Unload failed")
  try:
   if S.topology: S.topology.restore_all()
  except Exception: logger.exception("Restoring CPUs on unload failed")

 # ---- конфигурация ----------------------------------------------------
 async def get_config(self):
  try:
   if S.cfg is None: raise RuntimeError("config storage is not initialized")
   return await asyncio.to_thread(S.cfg.get_config)
  except asyncio.CancelledError:
   raise
  except Exception as e:
   logger.exception("AutoTDP: get_config failed, returning defaults: %s", e)
   cfg=ConfigManager.get_default_config()
   cfg["_backend_error"]=str(e)
   return cfg

 @_safe(False, 'set_config_value')
 async def set_config_value(self,key,value):
  if S.cfg is None: return False
  return bool(await asyncio.to_thread(S.cfg.set_value,key,value))

 @_safe(False, 'reset_config')
 async def reset_config(self):
  if S.cfg is None: return False
  return bool(await asyncio.to_thread(S.cfg.reset_to_defaults))

 @_safe(False, 'set_config')
 async def set_config(self,config):
  if S.cfg is None: return False
  ok,msg=S.cfg.validate_config(config)
  if not ok: return False
  return bool(await asyncio.to_thread(S.cfg.set_config,config))

 # ---- статистика ------------------------------------------------------
 @_safe(dict, 'get_stats')
 async def get_stats(self):
  def _stats():
   r={'tdp':S.tdp.stats() if S.tdp else {'backend':'none'},
      'fan':S.fan.get_stats() if S.fan else {'available':False},
      'epp_ok':S.epp is not None,'build':'2.1.1'}
   if S.epp: r.update(S.epp.get_current_stats())
   r['monitor']=S.monitor.get_stats() if S.monitor else {'state':'stopped'}
   r['cores']=S.topology.get_stats() if S.topology else {'available':False,'max_cores':0,'min_cores':2,'active_cores':0}
   if S.topology and S.topology.last_evacuation is not None:
    r['cores']['evacuation']={k:v for k,v in S.topology.last_evacuation.items() if k!='stuck'}
    r['cores']['evacuation_stuck']=len(S.topology.last_evacuation.get('stuck',[]))
   return r
  return await asyncio.to_thread(_stats)

 # ---- AutoTDP ---------------------------------------------------------
 @_safe(False, 'start_monitor')
 async def start_monitor(self,min_tdp=15,max_tdp=80,target_fps=40,enable_auto=True):
  if S.monitor is None or S.cfg is None: return False
  initial=await asyncio.to_thread(S.cfg.get_value,'initial_tdp',35)
  ok=await asyncio.to_thread(S.monitor.start,min_tdp,max_tdp,target_fps,initial)
  await asyncio.to_thread(S.cfg.set_value,'enabled',ok)
  return ok

 @_safe(False, 'stop_monitor')
 async def stop_monitor(self):
  try:
   ok=await asyncio.to_thread(S.monitor.stop,True) if S.monitor else True
  except Exception as e:
   logger.exception('stop_monitor: %s',e); ok=False
  if S.cfg: await asyncio.to_thread(S.cfg.set_value,'enabled',False)
  return ok

 @_safe(False, 'update_monitor_params')
 async def update_monitor_params(self,min_tdp=None,max_tdp=None,target_fps=None):
  ok=await asyncio.to_thread(S.monitor.set_parameters,min_tdp,max_tdp,target_fps) if S.monitor else False
  if S.cfg:
   if min_tdp is not None: await asyncio.to_thread(S.cfg.set_value,'min_tdp',float(min_tdp))
   if max_tdp is not None: await asyncio.to_thread(S.cfg.set_value,'max_tdp',float(max_tdp))
   if target_fps is not None: await asyncio.to_thread(S.cfg.set_value,'target_fps',int(target_fps))
  return ok

 @_safe(False, 'set_tdp')
 async def set_tdp(self,value):
  v=float(value)
  ok=await asyncio.to_thread(S.tdp.set_tdp,v)
  if ok and S.cfg: await asyncio.to_thread(S.cfg.set_value,'last_tdp',v)
  return ok

 @_safe(dict, 'set_active_cores')
 async def set_active_cores(self,cores):
  """Запускает изменение числа ядер в фоне и сразу возвращает ответ (версия 2.1.1).
  Ход выполнения читается через get_stats()['cores']['operation']."""
  if S.topology is None or not S.topology.available:
   return {'started':False,'error':'CPU topology not available'}
  res=await asyncio.to_thread(S.topology.start_apply,int(cores))
  return res

 @_safe(dict, 'get_tdp_stats')
 async def get_tdp_stats(self):
  return await asyncio.to_thread(S.tdp.stats)

 @_safe(dict, 'get_fan_stats')
 async def get_fan_stats(self):
  return await asyncio.to_thread(S.fan.get_stats)

 @_safe(False, 'set_mangohud_display')
 async def set_mangohud_display(self,enabled):
  enabled=bool(enabled)
  ok=await asyncio.to_thread(S.mangohud.set_display,enabled)
  if ok and S.cfg: await asyncio.to_thread(S.cfg.set_value,"mangohud_display",enabled)
  return ok

 # ---- вентилятор ------------------------------------------------------
 @_safe(False, 'set_fan_speed')
 async def set_fan_speed(self,speed):
  return await asyncio.to_thread(S.fan.set_fan_speed,int(speed))

 @_safe(list, 'get_fan_curve')
 async def get_fan_curve(self):
  return await asyncio.to_thread(S.fan.get_current_curve)

 @_safe(False, 'set_fan_curve')
 async def set_fan_curve(self,curve):
  ok=await asyncio.to_thread(S.fan.set_curve,curve)
  if S.cfg: await asyncio.to_thread(S.cfg.set_value,'fan_control.curve',S.fan.get_current_curve())
  return ok

 @_safe(False, 'reset_fan_curve')
 async def reset_fan_curve(self):
  ok=await asyncio.to_thread(S.fan.reset_curve)
  if S.cfg: await asyncio.to_thread(S.cfg.set_value,'fan_control.curve',S.fan.get_current_curve())
  return ok

 @_safe(False, 'enable_fan_control')
 async def enable_fan_control(self):
  ok=await asyncio.to_thread(S.fan.enable)
  if S.cfg: await asyncio.to_thread(S.cfg.set_value,'fan_control.enabled',ok)
  return ok

 @_safe(False, 'disable_fan_control')
 async def disable_fan_control(self):
  ok=await asyncio.to_thread(S.fan.disable)
  if S.cfg: await asyncio.to_thread(S.cfg.set_value,'fan_control.enabled',False)
  return ok

 # ---- профили ---------------------------------------------------------
 @_safe(dict, 'get_profiles')
 async def get_profiles(self):
  return S.cfg.get_all_profiles() if S.cfg else {}

 @_safe(False, 'load_profile')
 async def load_profile(self,name):
  p=S.cfg.get_profile(name)
  if not p: return False
  for k in ('min_tdp','max_tdp','target_fps'):
   if k in p: S.cfg.set_value(k,p[k])
  S.cfg.set_value('current_profile',name); return True

 @_safe(False, 'save_profile')
 async def save_profile(self,name,tdp_min,tdp_max,target_fps,description=''):
  return S.cfg.save_profile(name,{'min_tdp':tdp_min,'max_tdp':tdp_max,'target_fps':target_fps,'description':description})

 @_safe(False, 'delete_profile')
 async def delete_profile(self,name):
  return S.cfg.delete_profile(name)

 # ---- EPP / платформа -------------------------------------------------
 @_safe(False, 'set_epp')
 async def set_epp(self,value):
  if not S.epp: return False
  try: return S.epp.write_epp(int(value))
  except Exception: return False

 @_safe(-1, 'read_epp')
 async def read_epp(self):
  if not S.epp: return -1
  try: return S.epp.read_epp(0)
  except Exception: return -1

 @_safe(False, 'set_platform_profile')
 async def set_platform_profile(self,profile):
  if not S.epp: return False
  try: return S.epp.write_platform_profile(profile)
  except Exception: return False
