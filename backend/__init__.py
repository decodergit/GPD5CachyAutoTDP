# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
AutoTDP backend package.

Imports are relative (`.epp_controller`) so the package works regardless of
whether it is imported as `backend` (after main.py inserts the plugin dir
into sys.path) or under any other package name.

If an older install left absolute `backend.xxx` imports in place, or the
package is loaded in a context where relative imports fail, the fallback
below keeps things working.
"""

try:
    from .epp_controller import (
        EPPController,
        EPPControllerException,
        EPPNotAvailableException,
        PermissionDeniedException,
    )
    from .config_manager import ConfigManager, ConfigException
    from .monitor import TDPMonitor, TDPMonitorException
    from .fan_controller import FanController, FanControllerException
    from .tdp_controller import TDPController, TDPControllerException
    from .fps_reader import FPSReader
except ImportError:  # pragma: no cover — only hit if loaded as a bare module
    from epp_controller import (  # type: ignore
        EPPController,
        EPPControllerException,
        EPPNotAvailableException,
        PermissionDeniedException,
    )
    from config_manager import ConfigManager, ConfigException  # type: ignore
    from monitor import TDPMonitor, TDPMonitorException  # type: ignore
    from fan_controller import FanController, FanControllerException  # type: ignore

__all__ = [
    "EPPController",
    "EPPControllerException",
    "EPPNotAvailableException",
    "PermissionDeniedException",
    "ConfigManager",
    "ConfigException",
    "TDPMonitor",
    "TDPMonitorException",
    "FanController",
    "FanControllerException",
    "TDPController", "TDPControllerException", "FPSReader",
]
