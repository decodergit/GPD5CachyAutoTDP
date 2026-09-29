# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import logging, os, sys
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
Path(LOG_DIR).mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s',handlers=[logging.FileHandler(Path(LOG_DIR)/'plugin.log'),logging.StreamHandler()])
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
try:
 from backend.epp_controller import EPPController, EPPNotAvailableException
except Exception: EPPController=None

class Plugin:
 async def _main(self):
  logger.info("AutoTDP: _main start")
  try:
   self.cfg=ConfigManager(SETTINGS_DIR); self.cfg.load_config(); logger.info("AutoTDP: config ready")
   self.tdp=TDPController(); logger.info("AutoTDP: TDP ready backend=%s", self.tdp.backend)
   self.fan=FanController(); logger.info("AutoTDP: fan ready available=%s", self.fan.is_available())
   self.mangohud=MangoHudController(); logger.info("AutoTDP: MangoHud config=%s", self.mangohud.get_path())
   try:self.mangohud.set_display(bool(self.cfg.get_value("mangohud_display", False)))
   except Exception as e:logger.warning("MangoHud visibility setup failed: %s",e)
   self.epp=None
   if EPPController:
    try:self.epp=EPPController()
    except Exception as e:logger.info('EPP unavailable: %s',e)
   logger.info("AutoTDP: EPP stage complete")
   self.monitor=TDPMonitor(self.tdp,self.cfg,self.fan); logger.info("AutoTDP: monitor ready")
   fc=self.cfg.get_value('fan_control',{})
   if fc.get('enabled',True) and self.fan.is_available():
    try:
     self.fan.set_curve(fc.get('curve',self.fan.get_current_curve())); self.fan.enable()
     logger.info("AutoTDP: fan curve enabled")
    except Exception as e: logger.exception("Fan initialization failed: %s",e)
   if self.cfg.get_value('enabled',False) and self.tdp.available():
    try:self.monitor.start(self.cfg.get_value('min_tdp',15),self.cfg.get_value('max_tdp',55),self.cfg.get_value('target_fps',40),self.cfg.get_value('initial_tdp',35))
    except Exception as e:logger.exception("Saved AutoTDP start failed: %s",e)
   logger.info("AutoTDP: _main complete")
  except Exception as e:
   logger.exception("AutoTDP: initialization failed; plugin kept alive: %s",e)

 async def _unload(self):
  try:
   if getattr(self,'monitor',None): self.monitor.stop()
   if getattr(self,'fan',None): self.fan.disable()
  except Exception: logger.exception("Unload failed")

 async def get_config(self): return self.cfg.get_config()
 async def set_config_value(self,key,value): return self.cfg.set_value(key,value)
 async def reset_config(self): return self.cfg.reset_to_defaults()
 async def set_config(self,config):
  ok,msg=self.cfg.validate_config(config)
  if not ok:return False
  return self.cfg.set_config(config)
 async def get_stats(self):
  r={'tdp':self.tdp.stats(),'fan':self.fan.get_stats(),'epp_ok':self.epp is not None}
  if self.epp:r.update(self.epp.get_current_stats())
  r['monitor']=self.monitor.get_stats(); return r
 async def start_monitor(self,min_tdp=15,max_tdp=55,target_fps=40,enable_auto=True):
  try:
   ok=self.monitor.start(min_tdp,max_tdp,target_fps,self.cfg.get_value('initial_tdp',35)); self.cfg.set_value('enabled',ok); return ok
  except Exception as e:logger.exception('start_monitor: %s',e);return False
 async def stop_monitor(self):
  ok=self.monitor.stop();self.cfg.set_value('enabled',False);return ok
 async def update_monitor_params(self,min_tdp=None,max_tdp=None,target_fps=None):
  try:
   ok=self.monitor.set_parameters(min_tdp,max_tdp,target_fps)
   if min_tdp is not None:self.cfg.set_value('min_tdp',float(min_tdp))
   if max_tdp is not None:self.cfg.set_value('max_tdp',float(max_tdp))
   if target_fps is not None:self.cfg.set_value('target_fps',int(target_fps))
   return ok
  except Exception as e:
   logger.exception('update_monitor_params: %s',e); return False
 async def set_tdp(self,value):
  try:
   v=float(value); ok=self.tdp.set_tdp(v)
   if ok:self.cfg.set_value('last_tdp',v)
   return ok
  except Exception as e:logger.error('set_tdp: %s',e);return False
 async def get_tdp_stats(self):return self.tdp.stats()
 async def get_fan_stats(self):return self.fan.get_stats()
 async def set_mangohud_display(self,enabled):
  try:
   enabled=bool(enabled); ok=self.mangohud.set_display(enabled)
   if ok:self.cfg.set_value("mangohud_display",enabled)
   return ok
  except Exception as e:logger.error("set_mangohud_display: %s",e);return False
 async def set_fan_speed(self,speed):return self.fan.set_fan_speed(int(speed))
 async def get_fan_curve(self):return self.fan.get_current_curve()
 async def set_fan_curve(self,curve):
  ok=self.fan.set_curve(curve); self.cfg.set_value('fan_control.curve',self.fan.get_current_curve()); return ok
 async def reset_fan_curve(self):
  ok=self.fan.reset_curve();self.cfg.set_value('fan_control.curve',self.fan.get_current_curve());return ok
 async def enable_fan_control(self):
  ok=self.fan.enable();self.cfg.set_value('fan_control.enabled',ok);return ok
 async def disable_fan_control(self):
  ok=self.fan.disable();self.cfg.set_value('fan_control.enabled',False);return ok
 async def get_profiles(self):return self.cfg.get_all_profiles()
 async def load_profile(self,name):
  p=self.cfg.get_profile(name)
  if not p:return False
  for k in ('min_tdp','max_tdp','target_fps'):
   if k in p:self.cfg.set_value(k,p[k])
  self.cfg.set_value('current_profile',name);return True
 async def save_profile(self,name,tdp_min,tdp_max,target_fps,description=''):return self.cfg.save_profile(name,{'min_tdp':tdp_min,'max_tdp':tdp_max,'target_fps':target_fps,'description':description})
 async def delete_profile(self,name):return self.cfg.delete_profile(name)
 async def set_epp(self,value):
  if not self.epp:return False
  try:return self.epp.write_epp(int(value))
  except:return False
 async def read_epp(self):
  if not self.epp:return -1
  try:return self.epp.read_epp(0)
  except:return -1
 async def set_platform_profile(self,profile):
  if not self.epp:return False
  try:return self.epp.write_platform_profile(profile)
  except:return False
