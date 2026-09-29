# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import logging, threading, time
from typing import Any
from .tdp_controller import TDPController, TDPControllerException
from .fps_reader import FPSReader
logger=logging.getLogger(__name__)
class TDPMonitorException(Exception): pass
class TDPMonitor:
    STATE_STOPPED='stopped'; STATE_RUNNING='running'; STATE_WAITING='waiting'; STATE_ERROR='error'
    def __init__(self, tdp: TDPController, config_manager: Any, fan=None):
        self.tdp=tdp; self.cfg=config_manager; self.fan=fan; self.fps=FPSReader(); self._lock=threading.Lock(); self._stop=threading.Event(); self._thread=None
        self._running=False; self.state=self.STATE_STOPPED; self.target_fps=40; self.min_tdp=15.; self.max_tdp=55.; self.last_fps=None; self.last_tdp=None
        self._stats={'adjustments_made':0,'errors':0,'last_error':None,'total_runtime_sec':0}
    def start(self,min_tdp=15.,max_tdp=55.,target_fps=40,initial_tdp=None):
        if not self.tdp.available(): raise TDPMonitorException('No real TDP backend available')
        if min_tdp>max_tdp or target_fps<1: raise TDPMonitorException('Invalid monitor parameters')
        with self._lock:
            if self._running:return False
            self.min_tdp=max(self.tdp.min_w,float(min_tdp)); self.max_tdp=min(self.tdp.max_w,float(max_tdp)); self.target_fps=int(target_fps)
            cur=self.tdp.current_w
            if cur is None:
                saved_tdp=self.cfg.get_value('last_tdp',None)
                cur=saved_tdp if saved_tdp is not None else (initial_tdp if initial_tdp is not None else self.cfg.get_value('initial_tdp',35))
            cur=max(self.min_tdp,min(self.max_tdp,float(cur)))
            try:
                self.tdp.set_tdp(cur)
            except Exception as e:
                self.state=self.STATE_ERROR; self._stats['last_error']=str(e); self._stats['errors']+=1
                raise
            self.last_tdp=cur
            self.cfg.set_value('last_tdp',cur)
            self._running=True; self.state=self.STATE_WAITING
        self._stop.clear(); self._thread=threading.Thread(target=self._loop,daemon=True,name='AutoTDP'); self._thread.start(); return True
    def stop(self):
        with self._lock:self._running=False
        self._stop.set()
        if self._thread and self._thread.is_alive(): self._thread.join(3)
        with self._lock:self.state=self.STATE_STOPPED
        return True
    def set_parameters(self,min_tdp=None,max_tdp=None,target_fps=None):
        with self._lock:
            if min_tdp is not None:self.min_tdp=float(min_tdp)
            if max_tdp is not None:self.max_tdp=float(max_tdp)
            if self.min_tdp>self.max_tdp: self.min_tdp,self.max_tdp=self.max_tdp,self.min_tdp
            if target_fps is not None:self.target_fps=int(target_fps)
        return True
    def _loop(self):
        started=time.time(); last_change=0.; last_direction=0
        while not self._stop.is_set():
            try:
                fps=self.fps.read(); self.last_fps=fps
                cur=self.tdp.read_tdp()
                if cur is not None:self.last_tdp=cur
                # Strix Halo ryzenadj cannot expose the power metric table on this setup.
                # In that case last_tdp is our verified setpoint and is sufficient for control.
                if fps is None or self.last_tdp is None:
                    self.state=self.STATE_WAITING
                else:
                    cur=float(self.last_tdp)
                    err=float(fps)-float(self.target_fps)
                    # Adaptive convergence: far from target use larger jumps;
                    # at/above target probe downward by exactly 1 W. This is
                    # important when FPS is capped by gamescope/display (e.g. 60 FPS):
                    # we keep reducing TDP until FPS actually falls, then restore 1 W.
                    if err < -10.0:
                        direction, step = 1, 5.0
                    elif err < -5.0:
                        direction, step = 1, 2.0
                    elif err < 0.0:
                        direction, step = 1, 1.0
                    elif err >= 10.0:
                        direction, step = -1, 5.0
                    elif err > 5.0:
                        direction, step = -1, 2.0
                    else:
                        direction, step = -1, 1.0
                    now=time.time()
                    if direction == last_direction and now-last_change>=1.5:
                        new=max(self.min_tdp,min(self.max_tdp,cur + step*direction))
                        if abs(new-cur)>=0.5:
                            self.tdp.set_tdp(new); self.last_tdp=new; self.cfg.set_value('last_tdp',new); self._stats['adjustments_made']+=1; last_change=now
                    elif direction != last_direction:
                        # Allow the first correction immediately after crossing
                        # the target / changing direction, without waiting an extra cycle.
                        new=max(self.min_tdp,min(self.max_tdp,cur + step*direction))
                        if abs(new-cur)>=0.5:
                            self.tdp.set_tdp(new); self.last_tdp=new; self.cfg.set_value('last_tdp',new); self._stats['adjustments_made']+=1; last_change=now
                    last_direction=direction; self.state=self.STATE_RUNNING
                self._stats['total_runtime_sec']=int(time.time()-started)
            except Exception as e:
                logger.error('monitor: %s',e,exc_info=True); self._stats['errors']+=1; self._stats['last_error']=str(e); self.state=self.STATE_ERROR
            self._stop.wait(float(self.cfg.get_value('check_interval_sec',3)))
    def get_stats(self):
        with self._lock:
            return {'state':self.state,'running':self._running,'target_fps':self.target_fps,'min_tdp':self.min_tdp,'max_tdp':self.max_tdp,'last_fps':self.last_fps,'last_tdp':self.last_tdp,**self._stats,'fps_source':self.fps.path and str(self.fps.path)}
