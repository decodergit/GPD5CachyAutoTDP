# GPD5CachyAutoTDP 1.2.0

Decky Loader plugin for **GPD WIN 5 / AMD Ryzen AI MAX+ 395 (Strix Halo) / CachyOS Handheld**.

The plugin automatically adjusts TDP to the selected target FPS, boosts TDP during sustained high CPU/GPU load, and controls the GPD WIN 5 fan curve.


## Project status and purpose

GPD5CachyAutoTDP is a **temporary solution** for GPD WIN 5 / Ryzen AI MAX+ 395 (Strix Halo) on CachyOS Handheld. It is intended to bridge the current gap while native drivers, hardware-control utilities, and full GPD WIN 5 support are being developed for CachyOS/Linux. When proper upstream support becomes available, this plugin may no longer be necessary.

The project is provided as-is under the MIT License. Hardware-control operations can affect power limits, fan behavior, thermals, and system stability.

## License

The project source code is licensed under the **MIT License**. See [`LICENSE`](LICENSE). Third-party components retain their respective licenses; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## PowerControl prerequisite and conflict

**PowerControl must be installed before the first launch of GPD5CachyAutoTDP.**

Before the first launch:

1. Install PowerControl and make sure its `ryzenadj` executable is present.
2. **Deactivate PowerControl before launching GPD5CachyAutoTDP.** Do not run two TDP controllers simultaneously: both can write the same power-control interface.
3. Launch GPD5CachyAutoTDP once. During initialization it copies PowerControl's `ryzenadj` into its own `bin/` directory.
4. After GPD5CachyAutoTDP has initialized successfully and its local `bin/ryzenadj` exists, PowerControl may be removed.

PowerControl is therefore a **first-launch dependency**, not a permanent runtime dependency.

## MangoHud / FPS source

**MangoHud must always be enabled in the system while using GPD5CachyAutoTDP.** The plugin uses the continuous mangoapp/MangoHud CSV stream as its FPS source. Do not disable MangoHud globally.

**Recommended system/game setup:** keep system MangoHud/mangoapp enabled, and **disable FPS limiting both in the game and in the system/gamescope** while AutoTDP is active. Otherwise a 60 FPS (or other) cap can hide available performance and interfere with the controller's ability to find the minimum TDP.

GPD5CachyAutoTDP reads the live FPS stream from MangoHud/mangoapp CSV logs. MangoHud must remain active while a game is being controlled.

The plugin does **not** cache one CSV forever. Every few seconds it scans for the newest `mangoapp_*.csv`. If MangoHud/mangoapp is restarted and creates a new CSV, the plugin switches to the new file automatically. If the current CSV stops updating for several seconds, FPS is treated as unavailable rather than continuing to use stale values.

### MangoHud display control on CachyOS Handheld

CachyOS Handheld Edition uses **gamescope + mangoapp** for the system MangoHud overlay. This is different from a normal per-game `mangohud %command%` setup. GPD5CachyAutoTDP therefore uses the system `mangohudctl` IPC interface when it is available.

The final **MangoHud display** switch controls only visibility:

- **ON** — mangoapp HUD is visible;
- **OFF** — mangoapp HUD is hidden, while MangoHud/mangoapp and its CSV FPS logging remain active.

The switch is applied immediately to the running mangoapp when `mangohudctl` is available. It does **not** use `no_display=1` in the normal MangoHud config as the primary mechanism, because the Handheld gamescope session owns its MangoHud configuration and may replace it.

If `mangohudctl` is not available, the plugin falls back to the user's `~/.config/MangoHud/MangoHud.conf` for the next applicable MangoHud session.

**MangoHud/mangoapp must remain enabled in the CachyOS Handheld system.** Do not disable the system MangoHud/mangoapp service/session integration: GPD5CachyAutoTDP obtains FPS from its `mangoapp_*.csv` logs.

## High-load TDP boost

The **High-load TDP boost** option adds CPU/GPU utilization to the AutoTDP decision. By default the threshold is **95%**.

- If **CPU load stays above the threshold**, TDP is increased by **5 W** even when FPS is already at/above the target. This is intentional for CPU-bound work such as **shader compilation**, where FPS may look perfectly fine while a low TDP makes compilation much slower.
- If **GPU load stays above the threshold**, TDP is increased only when FPS is below the target. This prevents a hard 60 FPS cap from making a fully loaded GPU push TDP to the maximum unnecessarily.
- The configured Maximum TDP remains the hard ceiling.
- CPU/GPU load shown in the interface is the same Mangoapp telemetry used by the controller.

The threshold can be changed in the interface (90–100%).

## Automatic TDP algorithm

The controller uses adaptive steps:

- FPS deficit greater than 10: **+5 W**;
- FPS deficit from 5 to 10: **+2 W**;
- FPS deficit below 5: **+1 W**;
- FPS at or above target: **−1 W probing**.

When the target is reached, the controller deliberately reduces TDP by 1 W at a time until FPS actually falls below the target. It then restores 1 W. This is important for hard FPS caps such as 60 FPS: a reported 60 FPS does not mean that the current TDP is already minimal.

## Persisted settings

When **Auto TDP is switched off**, the plugin immediately restores the configured **Start TDP** value. This is deliberate: disabling automatic control returns the device to a predictable manual TDP instead of leaving the last adaptive setpoint active.

The following settings survive plugin restarts:

- Target FPS;
- Minimum TDP;
- Maximum TDP;
- Start TDP;
- AutoTDP enabled state;
- last AutoTDP TDP setpoint;
- fan curve settings.

## Compatibility

The frontend uses Decky's legacy IIFE format for compatibility with Decky Loader builds that evaluate `frontend_bundle` rather than loading ESM modules.

The backend uses `flags: ["root"]` because direct TDP and GPD fan control require root privileges on this hardware.


## License scope

The GPD5CachyAutoTDP source code is licensed under the MIT License, as stated
in `LICENSE`. Third-party software and runtime components are **not** relicensed
by this project; they remain under their respective upstream licenses listed
in `THIRD_PARTY_NOTICES.md`.

In particular, the repository does not distribute the RyzenAdj binary or the
PowerControl plugin. When an existing RyzenAdj executable from PowerControl
is detected during first-launch initialization, that executable remains
subject to its original LGPL-3.0-or-later license.
