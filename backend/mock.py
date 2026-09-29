# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Mock backend for local frontend development.

Replaces real hardware access with predictable stubs so frontend can be
tested and debugged without a Decky Loader environment or hardware access.

Import this instead of the real controllers:
    from backend.mock import (
        MockEPPController, MockConfigManager,
        MockTDPMonitor, MockFanController
    )
"""

import logging
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# ── Mock EPP Controller ──────────────────────────────────────────────────────

class MockEPPController:
    def __init__(self):
        self.cpu_count = 8
        self.epp_available = True
        self.platform_profile_available = True
        self._current_epp = 128
        self._current_profile = "balanced"

    def read_epp(self, cpu_id: int = 0) -> int:
        logger.debug("mock: read_epp(%d) -> %d", cpu_id, self._current_epp)
        return self._current_epp

    def write_epp(self, value: int) -> bool:
        if not (0 <= value <= 255):
            return False
        self._current_epp = value
        logger.debug("mock: write_epp(%d)", value)
        return True

    def read_platform_profile(self) -> str:
        logger.debug("mock: read_platform_profile() -> %s", self._current_profile)
        return self._current_profile

    def write_platform_profile(self, profile: str) -> bool:
        valid = ["performance", "balanced", "power-saver"]
        if profile not in valid:
            return False
        self._current_profile = profile
        logger.debug("mock: write_platform_profile(%s)", profile)
        return True

    def get_current_stats(self) -> Dict:
        return {
            "epp_available": self.epp_available,
            "platform_profile_available": self.platform_profile_available,
            "cpu_count": self.cpu_count,
            "current_epp": self._current_epp,
            "platform_profile": self._current_profile,
        }

    def epp_to_tdp_estimate(self, epp: int) -> float:
        tdp = 80.0 - (epp / 255.0) * 75.0  # 5W–80W range
        return round(tdp, 1)

    def tdp_estimate_to_epp(self, tdp: float) -> int:
        if tdp <= 5.0:
            return 255
        if tdp >= 80.0:
            return 0
        epp = int(255.0 * (80.0 - tdp) / 75.0)
        return max(0, min(255, epp))


# ── Mock Config Manager ──────────────────────────────────────────────────────

class MockConfigManager:
    DEFAULT_CONFIG: Dict[str, Any] = {
        "version": "1.0.3",
        "enabled": False,
        "target_fps": 40,
        "min_epp": 100,
        "max_epp": 200,
        "enable_auto_adjust": True,
        "check_interval_sec": 3,
        "hysteresis_threshold": 5,
        "current_profile": "balanced",
        "profiles": {
            "balanced": {"epp": 150, "description": "Balanced"},
            "performance": {"epp": 50, "description": "High performance"},
            "power_saver": {"epp": 240, "description": "Power saving"},
            "gaming": {"epp": 80, "description": "Gaming"},
        },
        "fan_control": {
            "enabled": True,
            "mode": "auto",
            "curve": {str(t): s for t, s in [(50, 20), (60, 25), (70, 35), (80, 55), (90, 85)]},
        },
    }

    def __init__(self, settings_dir: Optional[str] = None):
        self._config = self.DEFAULT_CONFIG.copy()
        logger.debug("mock: ConfigManager()")

    def get_config(self) -> Dict[str, Any]:
        return self._config

    def set_config(self, config: Dict[str, Any]) -> bool:
        self._config = config
        logger.debug("mock: set_config()")
        return True

    def get_value(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        node = self._config
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set_value(self, key: str, value: Any) -> bool:
        keys = key.split(".")
        node = self._config
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        logger.debug("mock: set_value(%s, %s)", key, value)
        return True

    def get_all_profiles(self) -> Dict[str, Any]:
        return self._config.get("profiles", {})

    def load_profile(self, name: str) -> bool:
        if name not in self.get_all_profiles():
            return False
        logger.debug("mock: load_profile(%s)", name)
        return True

    def save_profile(self, name: str, data: Dict[str, Any]) -> bool:
        if "profiles" not in self._config:
            self._config["profiles"] = {}
        self._config["profiles"][name] = data
        logger.debug("mock: save_profile(%s)", name)
        return True

    def delete_profile(self, name: str) -> bool:
        if "profiles" in self._config and name in self._config["profiles"]:
            del self._config["profiles"][name]
            logger.debug("mock: delete_profile(%s)", name)
            return True
        return False

    def reset_to_defaults(self) -> bool:
        self._config = self.DEFAULT_CONFIG.copy()
        logger.debug("mock: reset_to_defaults()")
        return True

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        for key in ("version", "enabled", "target_fps", "min_epp", "max_epp"):
            if key not in config:
                return False, f"Missing: {key}"
        return True, ""


# ── Mock TDP Monitor ─────────────────────────────────────────────────────────

class MockTDPMonitor:
    STATE_RUNNING = "running"

    def __init__(self, epp_controller, config_manager):
        self._epp = epp_controller
        self._cfg = config_manager
        self._running = False
        self._adjustments = 0
        logger.debug("mock: TDPMonitor()")

    def start(
        self,
        min_epp: int = 100,
        max_epp: int = 200,
        target_fps: int = 40,
        enable_auto: bool = True,
    ) -> bool:
        self._running = True
        logger.debug("mock: TDPMonitor.start()")
        return True

    def stop(self) -> bool:
        self._running = False
        logger.debug("mock: TDPMonitor.stop()")
        return True

    def set_parameters(
        self,
        min_epp: Optional[int] = None,
        max_epp: Optional[int] = None,
        target_fps: Optional[int] = None,
    ) -> bool:
        logger.debug("mock: TDPMonitor.set_parameters()")
        return True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self.STATE_RUNNING if self._running else "stopped",
            "running": self._running,
            "last_epp": 128 if self._running else None,
            "adjustments_made": self._adjustments,
            "total_runtime_sec": 42,
            "errors": 0,
            "last_error": None,
        }


# ── Mock Fan Controller ──────────────────────────────────────────────────────

class MockFanController:
    def __init__(self):
        self._enabled = False
        self._current_speed = 0
        self._current_temp = 55.0
        self._curve = {50: 20, 60: 25, 70: 35, 80: 55, 90: 85}
        logger.debug("mock: FanController()")

    def is_available(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> bool:
        self._enabled = True
        logger.debug("mock: FanController.enable()")
        return True

    def disable(self) -> bool:
        self._enabled = False
        logger.debug("mock: FanController.disable()")
        return True

    def read_temperature(self) -> Optional[float]:
        return self._current_temp

    def set_fan_speed(self, speed_percent: int) -> bool:
        if not (0 <= speed_percent <= 100):
            return False
        self._current_speed = speed_percent
        logger.debug("mock: FanController.set_fan_speed(%d%%)", speed_percent)
        return True

    def calculate_fan_speed(self, temperature: float) -> int:
        pts = sorted(self._curve.items())
        if temperature <= pts[0][0]:
            return pts[0][1]
        if temperature >= pts[-1][0]:
            return pts[-1][1]
        for (t1, s1), (t2, s2) in zip(pts, pts[1:]):
            if t1 <= temperature <= t2:
                frac = (temperature - t1) / (t2 - t1)
                return max(0, min(100, int(s1 + frac * (s2 - s1))))
        return pts[-1][1]

    def set_curve(self, curve: Dict[int, int]) -> bool:
        self._curve = curve
        logger.debug("mock: FanController.set_curve()")
        return True

    def reset_curve(self) -> bool:
        self._curve = {50: 20, 60: 25, 70: 35, 80: 55, 90: 85}
        logger.debug("mock: FanController.reset_curve()")
        return True

    def get_current_curve(self) -> Dict[int, int]:
        return self._curve.copy()

    def get_stats(self) -> Dict:
        return {
            "available": True,
            "enabled": self._enabled,
            "current_temperature": self._current_temp,
            "calculated_fan_speed": (
                self.calculate_fan_speed(self._current_temp) if self._enabled else None
            ),
            "hwmon_path": "/sys/class/hwmon/hwmon0",
        }
