# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
"""
EPP (Energy Performance Preference) Controller for AMD Strix Halo / amd_pstate.
"""

import glob
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EPPControllerException(Exception):
    pass


class EPPNotAvailableException(EPPControllerException):
    pass


class PermissionDeniedException(EPPControllerException):
    pass


class EPPController:
    """
    Controls CPU power/performance via sysfs amd_pstate interface.

    Interfaces used:
      /sys/firmware/acpi/platform_profile
      /sys/devices/system/cpu/cpuN/cpufreq/energy_performance_preference
    """

    PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"
    EPP_BASE_PATH = "/sys/devices/system/cpu/cpu{}/cpufreq/energy_performance_preference"

    EPP_MIN = 0
    EPP_MAX = 255
    EPP_DEFAULT = 128

    # TDP range for Strix Halo / GPD Win 5
    TDP_MIN_W = 5.0
    TDP_MAX_W = 80.0

    def __init__(self):
        self.cpu_count = self._get_cpu_count()
        self.platform_profile_available = self._check_platform_profile()
        self.epp_available = self._check_epp_available()

        if not self.epp_available and not self.platform_profile_available:
            raise EPPNotAvailableException(
                "Neither EPP nor platform_profile is available. "
                "Requires amd_pstate driver with EPP support."
            )

        logger.info(
            "EPPController: cpus=%d epp=%s profile=%s",
            self.cpu_count,
            self.epp_available,
            self.platform_profile_available,
        )

    def _get_cpu_count(self) -> int:
        # cpu[0-9]* matches cpu0…cpu9, cpu10…cpu15, etc.
        paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*")
        count = sum(1 for p in paths if os.path.basename(p)[3:].isdigit())
        return count if count > 0 else 4

    def _check_platform_profile(self) -> bool:
        return os.path.exists(self.PLATFORM_PROFILE_PATH) and os.access(
            self.PLATFORM_PROFILE_PATH, os.R_OK
        )

    def _check_epp_available(self) -> bool:
        path = self.EPP_BASE_PATH.format(0)
        return os.path.exists(path) and os.access(path, os.R_OK)

    # ------------------------------------------------------------------
    # EPP read / write
    # ------------------------------------------------------------------

    def read_epp(self, cpu_id: int = 0) -> int:
        if not self.epp_available:
            raise EPPNotAvailableException("EPP not available")
        path = self.EPP_BASE_PATH.format(cpu_id)
        try:
            with open(path, "r") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            raise EPPControllerException(f"CPU {cpu_id} not found")
        except (ValueError, OSError) as e:
            raise EPPControllerException(f"Failed to read EPP cpu{cpu_id}: {e}")

    def write_epp(self, value: int) -> bool:
        if not self.epp_available:
            raise EPPNotAvailableException("EPP not available")
        if not (self.EPP_MIN <= value <= self.EPP_MAX):
            raise EPPControllerException(
                f"EPP must be {self.EPP_MIN}-{self.EPP_MAX}, got {value}"
            )

        errors: List[str] = []
        for cpu_id in range(self.cpu_count):
            path = self.EPP_BASE_PATH.format(cpu_id)
            try:
                with open(path, "w") as f:
                    f.write(str(value))
            except PermissionError:
                errors.append(f"cpu{cpu_id}: permission denied")
            except OSError as e:
                errors.append(f"cpu{cpu_id}: {e}")

        if errors:
            if len(errors) == self.cpu_count:
                raise PermissionDeniedException(
                    "Failed to write EPP to any CPU: " + "; ".join(errors)
                )
            logger.warning("EPP write partial errors: %s", "; ".join(errors))

        logger.debug("Wrote EPP=%d to all CPUs", value)
        return True

    # ------------------------------------------------------------------
    # Platform profile
    # ------------------------------------------------------------------

    def read_platform_profile(self) -> str:
        if not self.platform_profile_available:
            raise EPPNotAvailableException("Platform profile not available")
        try:
            with open(self.PLATFORM_PROFILE_PATH, "r") as f:
                return f.read().strip()
        except OSError as e:
            raise EPPControllerException(f"Failed to read platform_profile: {e}")

    def write_platform_profile(self, profile: str) -> bool:
        valid = ["performance", "balanced", "power-saver"]
        if profile not in valid:
            raise EPPControllerException(
                f"Invalid profile '{profile}'. Must be one of {valid}"
            )
        try:
            with open(self.PLATFORM_PROFILE_PATH, "w") as f:
                f.write(profile)
            return True
        except PermissionError:
            raise PermissionDeniedException(
                "Permission denied writing platform_profile"
            )
        except OSError as e:
            raise EPPControllerException(f"Failed to write platform_profile: {e}")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_current_stats(self) -> Dict:
        stats: Dict = {
            "epp_available": self.epp_available,
            "platform_profile_available": self.platform_profile_available,
            "cpu_count": self.cpu_count,
        }
        if self.epp_available:
            try:
                stats["current_epp"] = self.read_epp(0)
            except Exception as e:
                stats["current_epp"] = None
                stats["epp_error"] = str(e)
        if self.platform_profile_available:
            try:
                stats["platform_profile"] = self.read_platform_profile()
            except Exception as e:
                stats["platform_profile"] = None
                stats["profile_error"] = str(e)
        return stats

    # ------------------------------------------------------------------
    # Conversion helpers  (EPP 0 = max perf/max TDP, 255 = min perf/min TDP)
    # ------------------------------------------------------------------

    def epp_to_tdp_estimate(self, epp: int) -> float:
        tdp = self.TDP_MAX_W - (epp / 255.0) * (self.TDP_MAX_W - self.TDP_MIN_W)
        return round(tdp, 1)

    def tdp_estimate_to_epp(self, tdp: float) -> int:
        if tdp <= self.TDP_MIN_W:
            return 255
        if tdp >= self.TDP_MAX_W:
            return 0
        epp = int(
            255.0 * (self.TDP_MAX_W - tdp) / (self.TDP_MAX_W - self.TDP_MIN_W)
        )
        return max(0, min(255, epp))
