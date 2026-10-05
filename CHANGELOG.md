# Changelog

## 1.2.0

- Added sustained high-load TDP boost using Mangoapp CPU/GPU utilization.
- CPU > threshold can raise TDP even when FPS is already above target, addressing CPU-bound shader compilation at low TDP.
- GPU > threshold raises TDP only when FPS is below target, avoiding FPS-cap-induced maximum TDP.
- Added CPU/GPU load telemetry and high-load boost controls to the Decky UI.
- Disabling Auto TDP now restores the configured Start TDP immediately.
- Added explicit MangoHud and uncapped-FPS recommendations to the README and UI.

## 1.1.0

- Clarified third-party license boundaries and runtime RyzenAdj handling. - 2026-09-29

- Prepared the project for public GitHub release.
- Added/clarified MIT licensing and third-party notices.
- Documented the project's temporary status pending native GPD WIN 5 drivers, utilities, and CachyOS support.
- Preserved adaptive TDP control, GPD fan control, MangoHud/mangoapp CSV tracking, and system MangoHud display control.
- Removed the fixed TDP-step setting in favor of adaptive 5/2/1 W control and 1 W probing at the target FPS.
