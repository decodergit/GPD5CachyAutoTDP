# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
Configuration Manager for AutoTDP plugin.
"""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ConfigException(Exception):
    pass


class ConfigManager:
    CONFIG_FILENAME = "config.json"

    DEFAULT_CONFIG: Dict[str, Any] = {
        "version": "1.0.0",
        "enabled": False,
        "target_fps": 40,
        "min_tdp": 15,
        "max_tdp": 55,
        "initial_tdp": 35,
        "last_tdp": None,
        "mangohud_display": False,
        "enable_auto_adjust": True,
        "check_interval_sec": 3,
        "hysteresis_threshold": 5,
        "current_profile": "balanced",
        "profiles": {
            "balanced": {
                "epp": 150,
                "description": "Balanced performance and power",
            },
            "performance": {
                "epp": 50,
                "description": "High performance, higher power draw",
            },
            "power_saver": {
                "epp": 240,
                "description": "Maximum power saving",
            },
            "gaming": {
                "epp": 80,
                "description": "Optimized for gaming",
            },
        },
        "fan_control": {
            "enabled": True,
            "mode": "auto",
            "curve": {
                "50": 20,
                "60": 25,
                "65": 30,
                "70": 35,
                "75": 42,
                "80": 55,
                "85": 70,
                "90": 85,
                "95": 100,
            },
        },
    }

    def __init__(self, settings_dir: Optional[str] = None):
        if settings_dir is None:
            settings_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR")
            if not settings_dir:
                raise ConfigException("DECKY_PLUGIN_SETTINGS_DIR not set")

        self.settings_dir = Path(settings_dir)
        self.config_path = self.settings_dir / self.CONFIG_FILENAME
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self._config: Optional[Dict[str, Any]] = None
        logger.info("ConfigManager: %s", self.settings_dir)

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return copy.deepcopy(cls.DEFAULT_CONFIG)

    # ------------------------------------------------------------------

    def load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    loaded = json.load(f)
                # Merge with defaults so new keys are always present
                merged = self.get_default_config()
                merged.update(loaded)
                # TDP step was removed in AutoTDP 1.0.0; old configs are migrated silently.
                merged.pop("tdp_step", None)
                # Migrate the old EPP-only configuration. Never interpret EPP as a TDP value.
                if "min_tdp" not in loaded:
                    merged["min_tdp"] = 15
                    merged["max_tdp"] = 55
                if "initial_tdp" not in loaded:
                    merged["initial_tdp"] = min(35, merged["max_tdp"])
                self._config = merged
                logger.info("Loaded config from %s", self.config_path)
            except json.JSONDecodeError as e:
                raise ConfigException(f"Invalid JSON in config: {e}")
            except OSError as e:
                raise ConfigException(f"Cannot read config: {e}")
        else:
            self._config = self.get_default_config()
            self.save_config()
            logger.info("Created default config at %s", self.config_path)
        return self._config

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        if config is not None:
            self._config = config
        if self._config is None:
            raise ConfigException("No config loaded")
        try:
            with open(self.config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            return True
        except OSError as e:
            raise ConfigException(f"Cannot write config: {e}")

    def get_config(self) -> Dict[str, Any]:
        if self._config is None:
            return self.load_config()
        return self._config

    def set_config(self, config: Dict[str, Any]) -> bool:
        self._config = config
        return self.save_config()

    def get_value(self, key: str, default: Any = None) -> Any:
        if self._config is None:
            self.load_config()
        keys = key.split(".")
        node: Any = self._config
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set_value(self, key: str, value: Any) -> bool:
        if self._config is None:
            self.load_config()
        keys = key.split(".")
        if not keys:
            raise ConfigException("Empty key")
        node = self._config
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            if not isinstance(node[k], dict):
                raise ConfigException(f"Non-dict node at '{k}'")
            node = node[k]
        node[keys[-1]] = value
        return self.save_config()

    # ------------------------------------------------------------------

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        return self.get_value("profiles", {}).get(name)

    def save_profile(self, name: str, data: Dict[str, Any]) -> bool:
        if self._config is None:
            self.load_config()
        self._config.setdefault("profiles", {})[name] = data
        return self.save_config()

    def delete_profile(self, name: str) -> bool:
        if self._config is None:
            self.load_config()
        profiles = self._config.get("profiles", {})
        if name in profiles:
            del profiles[name]
            return self.save_config()
        return False

    def get_all_profiles(self) -> Dict[str, Any]:
        return self.get_value("profiles", {})

    def load_profile(self, name: str) -> bool:
        profile = self.get_profile(name)
        if profile is None:
            raise ConfigException(f"Profile not found: {name}")
        for key in ("min_tdp", "max_tdp", "target_fps"):
            if key in profile:
                self.set_value(key, profile[key])
        self.set_value("current_profile", name)
        return True

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(config.get("enabled", False), bool): return False, "enabled must be bool"
        if not (1 <= int(config.get("target_fps",40)) <= 120): return False, "target_fps must be 1-120"
        if float(config.get("min_tdp",15)) > float(config.get("max_tdp",55)): return False, "min_tdp must be <= max_tdp"
        return True, ""

    def reset_to_defaults(self) -> bool:
        self._config = self.get_default_config()
        logger.warning("Config reset to defaults")
        return self.save_config()
