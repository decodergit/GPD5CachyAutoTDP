# SPDX-License-Identifier: MIT
# Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import os
import re
import shutil
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MangoHudController:
    """Control the system MangoHud/mangoapp used by CachyOS Handheld's gamescope session.

    CachyOS Handheld Game Mode uses mangoapp rather than a normal per-game
    MangoHud Vulkan layer.  The supported live control path is mangohudctl,
    which talks to the running mangoapp through its IPC queue.  We use that
    first so the HUD can be hidden/shown immediately without disabling FPS
    logging.  A best-effort config fallback is retained for sessions where
    mangohudctl is unavailable.
    """

    MARKER_BEGIN = "# GPD5CachyAutoTDP managed MangoHud visibility - BEGIN"
    MARKER_END = "# GPD5CachyAutoTDP managed MangoHud visibility - END"

    def __init__(self):
        self.control = self._find_control()
        self.path = self._find_user_config()
        logger.info("MangoHud controller: mangohudctl=%s user_config=%s", self.control or "not found", self.path)

    @staticmethod
    def _find_control():
        candidates = [
            shutil.which("mangohudctl"),
            "/usr/bin/mangohudctl",
            "/usr/local/bin/mangohudctl",
        ]
        for p in candidates:
            if p and Path(p).is_file() and os.access(p, os.X_OK):
                return str(p)
        return None

    @staticmethod
    def _find_user_config():
        home = Path(os.environ.get("HOME", "/home/deck"))
        candidates = [
            home / ".config" / "MangoHud" / "MangoHud.conf",
            home / ".config" / "MangoHud" / "mangohud.conf",
        ]
        return next((p for p in candidates if p.exists()), candidates[0])

    def _run_ctl(self, enabled: bool) -> bool:
        if not self.control:
            return False
        # mangoapp's control protocol uses no_display=true to hide the HUD.
        # It does not stop the mangoapp instance or its CSV logger.
        no_display = "false" if enabled else "true"
        try:
            r = subprocess.run(
                [self.control, "set", "no_display", no_display],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if r.returncode == 0:
                logger.info("MangoHud/mangoapp display %s via mangohudctl", "enabled" if enabled else "hidden")
                return True
            logger.warning("mangohudctl failed rc=%s: %s", r.returncode, (r.stderr or r.stdout).strip())
        except Exception as e:
            logger.warning("mangohudctl invocation failed: %s", e)
        return False

    def _strip_managed(self, text):
        pattern = re.escape(self.MARKER_BEGIN) + r".*?" + re.escape(self.MARKER_END) + r"\s*\n?"
        return re.sub(pattern, "", text, flags=re.S)

    def _write_user_fallback(self, enabled: bool) -> bool:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = path.read_text() if path.exists() else ""
            lines = [line for line in text.splitlines() if line.strip() not in ("no_display", "no_display=1", "no_display=0")]
            text = self._strip_managed("\n".join(lines).rstrip())
            block = (
                f"{self.MARKER_BEGIN}\n"
                f"no_display={'0' if enabled else '1'}\n"
                f"{self.MARKER_END}\n"
            )
            path.write_text((text + "\n\n" if text else "") + block)
            logger.info("MangoHud visibility fallback written to %s", path)
            return True
        except OSError as e:
            logger.error("Cannot update MangoHud config %s: %s", path, e)
            return False

    def set_display(self, enabled: bool):
        enabled = bool(enabled)
        # This is the important path for CachyOS Handheld / gamescope mangoapp.
        # It changes the running overlay immediately and leaves logging active.
        if self._run_ctl(enabled):
            return True
        # If mangoapp is not currently running, preserve the preference for
        # sessions which use the user's MangoHud config. A later game launch
        # can then pick it up.
        return self._write_user_fallback(enabled)

    def get_path(self):
        return str(self.path)
