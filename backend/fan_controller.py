# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, List
logger=logging.getLogger(__name__)
class FanControllerException(Exception): pass
class FanController:
    DEFAULT_CURVE={50:20,60:25,65:30,70:35,75:42,80:55,85:70,90:85,95:100}
    def __init__(self):
        self.devices=[]; self.temp_path=None; self.curve=self.DEFAULT_CURVE.copy(); self.enabled=False; self._detect(); self._stop=threading.Event(); self._thread=None
    def _detect(self):
        base=Path('/sys/class/hwmon')
        if not base.exists():return
        # GPD fan controller is authoritative; temperature is preferably k10temp.
        for d in sorted(base.glob('hwmon*')):
            try:name=(d/'name').read_text().strip()
            except: name=''
            pwms=[p for p in d.glob('pwm[0-9]*') if p.name[3:].isdigit()]
            if name in ('gpd_fan','gpd-fan','gpdfan') and pwms:
                self.devices=[(p,d/(p.name+'_enable')) for p in pwms]; break
        preferred=[]
        for d in sorted(base.glob('hwmon*')):
            try:name=(d/'name').read_text().strip()
            except:name=''
            if name in ('k10temp','zenpower','cpu_thermal'):preferred += sorted(d.glob('temp*_input'))
        self.temp_path=preferred[0] if preferred else None
    def is_available(self):return bool(self.devices and self.temp_path)
    def read_temperature(self):
        if not self.temp_path:return None
        try:return int(self.temp_path.read_text())/1000
        except:return None
    def _mode(self,manual):
        for _,e in self.devices:
            if e.exists():
                try:e.write_text('1' if manual else '2')
                except Exception as x:logger.warning('fan mode: %s',x)
    def set_fan_speed(self,speed):
        if not self.devices:return False
        pwm=max(0,min(255,int(round(speed*255/100))))
        ok=True
        for p,_ in self.devices:
            try:p.write_text(str(pwm))
            except Exception as e:logger.warning('fan pwm: %s',e);ok=False
        return ok
    def calc(self,t):
        pts=sorted(self.curve.items())
        if t<=pts[0][0]:return pts[0][1]
        if t>=pts[-1][0]:return pts[-1][1]
        for (a,sa),(b,sb) in zip(pts,pts[1:]):
            if a<=t<=b:return round(sa+(t-a)*(sb-sa)/(b-a))
        return pts[-1][1]
    def apply(self):
        if not self.enabled:return False
        t=self.read_temperature()
        return self.set_fan_speed(self.calc(t)) if t is not None else False
    def enable(self):
        if not self.is_available():return False
        self._mode(True); self.enabled=True; self.start_background(); return True
    def disable(self):
        self.enabled=False; self._stop.set()
        if self._thread and self._thread.is_alive(): self._thread.join(2)
        self._mode(False); return True
    def start_background(self, interval=2.0):
        if not self.is_available(): return False
        if self._thread and self._thread.is_alive(): return True
        self._stop.clear(); self._thread=threading.Thread(target=self._loop,daemon=True,name='FanCurve'); self._thread.start(); return True
    def _loop(self):
        while not self._stop.is_set():
            try:
                self.apply()
            except Exception as e:
                logger.debug('fan loop: %s',e)
            self._stop.wait(2.0)
    def set_curve(self,c):
        self.curve={int(k):int(v) for k,v in c.items()}; return True
    def get_current_curve(self):return dict(self.curve)
    def reset_curve(self):self.curve=self.DEFAULT_CURVE.copy();return True
    def get_stats(self):
        t=self.read_temperature()
        rpm=[]; pwm=[]
        for p,_ in self.devices:
            try: pwm.append(round(int(p.read_text().strip()) * 100.0 / 255.0, 1))
            except Exception: pwm.append(None)
        for p,_ in self.devices:
            n=p.name[3:]
            rp=p.parent / ('fan' + n + '_input')
            try: rpm.append(int(rp.read_text().strip()))
            except Exception: rpm.append(None)
        return {'available':self.is_available(),'enabled':self.enabled,'current_temperature':t,'calculated_fan_speed':self.calc(t) if t is not None else None,'channels':len(self.devices),'pwm_percent':pwm,'fan_rpm':rpm}
