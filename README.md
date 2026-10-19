# GPD5CachyAutoTDP

Decky Loader plugin for **GPD WIN 5 / AMD Ryzen AI MAX+ 395 (Strix Halo) / CachyOS Handheld**.

GPD5CachyAutoTDP adjusts the TDP automatically to keep a target FPS, raises the TDP during sustained high CPU or GPU load, and controls the GPD WIN 5 fan curve.

> Русская версия: [README_RUS.md](README_RUS.md)

## Project status

GPD5CachyAutoTDP is a **temporary solution** for GPD WIN 5 / Ryzen AI MAX+ 395 (Strix Halo) on CachyOS Handheld. It bridges the gap until native drivers, hardware-control utilities and full GPD WIN 5 support are available for CachyOS/Linux. When proper upstream support exists, this plugin may no longer be needed.

The project is provided as-is under the MIT License. Hardware-control operations can affect power limits, fan behavior, thermals and system stability.

## Requirements

- GPD WIN 5 with AMD Ryzen AI MAX+ 395 (Strix Halo), running CachyOS Handheld Edition.
- Decky Loader.
- **MangoHud / mangoapp** enabled in the system. The plugin reads FPS from its CSV log.
- **PowerControl** installed before the first launch, so that its `ryzenadj` can be copied (see below).
- Root privileges: the plugin runs with `flags: ["root"]`, because TDP and fan control require root on this hardware.

## Features

- **Automatic TDP control to a target FPS.** You set a Target FPS; the plugin keeps the frame rate at or slightly above it and lowers the TDP when there is spare performance.
- **Minimum and maximum TDP** limits, and a **Start TDP** that is applied when Auto TDP is switched off.
- **High-load TDP boost.** Sustained high CPU load raises the TDP even when FPS is on target, which helps shader compilation. High GPU load raises the TDP only when FPS is below target. The threshold is adjustable (90–100 %).
- **Plateau detection.** If raising the TDP no longer increases FPS, the TDP is capped at that level for a while, so the plugin does not keep spending power for nothing.
- **Fan curve control** on the GPD WIN 5 PWM fan controller, with a temperature-to-speed curve and an in-plugin curve editor (temperature and speed per point, add and remove points, save and reset).
- **MangoHud display switch.** Shows or hides the mangoapp overlay while keeping FPS logging active.
- **English and Русский interface.** The language is chosen at the bottom of the screen and saved in the configuration.
- **Poll interval** is adjustable in the interface: shorter reacts faster, at the cost of reading the MangoHud log more often.
- **Search status.** The interface shows whether the controller is still looking for the lowest TDP, the levels it already trusts, and how many tries it made.
- **Initialization errors** are listed in the Status section, so a missing backend or fan controller is visible without reading the log.
- **Saved settings.** Target FPS, limits, Start TDP, the enabled state, the last TDP setpoint, the fan curve and the language survive restarts.

## How it works

### FPS source

The plugin reads the live FPS stream from the MangoHud/mangoapp CSV logs. Every few seconds it looks for the newest `mangoapp_*.csv`, so a restarted MangoHud is picked up automatically. If the file stops updating for several seconds, FPS is treated as unavailable and the plugin does not act on stale values.

### TDP control

Each control cycle the plugin:

1. Reads the FPS and the CPU/GPU load.
2. Compares the smoothed FPS with an **effective goal**, which is the Target FPS plus a small margin of 2 FPS.
3. Inside a dead band around the goal, it changes nothing.
4. When FPS is below the goal, it raises the TDP by a step proportional to the available TDP range and to the shortfall in frames: a large shortfall on a wide range gives a big step, a small shortfall near the goal gives a small one. The step is capped so it cannot jump far past the working level. The poll interval is adjustable (0.5–5 s, default 1 s): a shorter interval reacts faster and raises the TDP sooner. The plateau window and the raise interval follow it.
5. When FPS stays above the goal for a few seconds, it **searches for the lowest TDP that still holds the goal** by halving the interval. It remembers the lowest level that held the goal and the highest level that did not, and tries the middle of that interval. A successful try moves the upper bound down; a failed try (FPS below the goal) is undone at once and moves the lower bound up. The search ends when the interval is 2 W or less, usually after 4–6 tries. A single frame above the goal does not lower the TDP.
6. If a raise does not bring FPS up, the TDP is capped at that level for a while.
7. The search bounds are forgotten when the scene becomes heavier (FPS drops below the goal at the found level), after any raise, and after 90 seconds. If FPS stays well above the goal after the search has finished, a new search starts from the current level.

The TDP is always kept between the configured Minimum and Maximum. The Maximum never exceeds the hardware limit of 80 W.

### CPU and GPU load boost

CPU load above the threshold raises the TDP in steps, independent of FPS, because CPU-bound work such as shader compilation does not show up as FPS loss. GPU load raises the TDP only when FPS is below target, so a hard FPS cap does not push the TDP to the maximum. The plateau cap also limits the boost.

### Fan control

The fan follows the configured curve: a temperature (°C) maps to a fan speed (%). The curve must rise monotonically: higher temperatures never give a lower fan speed. The fan is returned to automatic control when the plugin is disabled.

To keep the fan quiet and steady:

- **Hysteresis.** The target speed is recalculated only after the temperature has moved more than 2 °C, so small fluctuations around a curve bend do not make the fan oscillate.
- **Dead band.** A change of less than 2 % is not written to the controller.
- **Ramp limit.** The speed rises by at most 25 % per second and falls by at most 10 % per second. Fast heating still gets a quick response.
- **Minimum speed.** While control is on, the fan never drops below 18 %.
- **Feed-forward.** When the TDP is raised, the target speed is increased by 1.5 % per watt for 8 seconds (at most 30 %), so the fan starts speeding up before the temperature rises. Lowering the TDP adds nothing.
- **Sensors.** The highest temperature among all found CPU sensors is used, so one failing sensor does not stop the control.

### Startup and recovery

If AutoTDP stays in the waiting state for more than 10 seconds after startup, the plugin reinitializes the backend. This recovers from a known post-reboot condition, where the plugin can stay stuck until it is reloaded. A 30-second cooldown prevents restart loops.

When the plugin is unloaded, all CPUs are switched back online, so no core is left disabled.

## Installation and first launch

**PowerControl must be installed before the first launch of GPD5CachyAutoTDP.**

1. Install PowerControl and make sure its `ryzenadj` executable is present.
2. **Deactivate PowerControl before launching GPD5CachyAutoTDP.** Two TDP controllers must not run at the same time, because both can write the same power-control interface.
3. Launch GPD5CachyAutoTDP once. During initialization it copies PowerControl's `ryzenadj` into its own `bin/` directory.
4. After GPD5CachyAutoTDP has initialized and its local `bin/ryzenadj` exists, PowerControl may be removed.

PowerControl is therefore a **first-launch dependency**, not a permanent runtime dependency.

## MangoHud and FPS settings

**MangoHud must stay enabled in the system while the plugin is used.** Do not disable MangoHud or mangoapp globally.

For best results, disable the FPS limit **both in the game and in the system or gamescope** while Auto TDP is active. A cap at 60 FPS (or any other value) hides the performance that is actually available, and prevents the controller from finding the lowest TDP that still reaches the target.

On CachyOS Handheld, MangoHud is provided by gamescope and mangoapp for the whole session, rather than per game. When the system `mangohudctl` interface is available, the **MangoHud display** switch uses it to show or hide the overlay immediately. Otherwise the plugin changes the MangoHud configuration file for the next session. Hiding the overlay does not stop FPS logging.

## License

The project source code is licensed under the **MIT License**. See [`LICENSE`](LICENSE).

Third-party components keep their own licenses; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The repository does not distribute the RyzenAdj binary or the PowerControl plugin. When an existing RyzenAdj executable from PowerControl is found during first-launch initialization, it remains subject to its original LGPL-3.0-or-later license.

## Building from source

The frontend is built from `src/` with rollup:

```bash
npm install
npm run build   # dist/index.js
```

The backend is plain Python and needs no build step.

## On-device checks

The `tools/` directory has two scripts: `collect_metrics.py` records TDP, FPS, temperature and fan speed to a CSV while you play, and `analyze_metrics.py` reports how fast the TDP falls, how often it changes, and whether lowering the TDP causes FPS drops. Both only read the system. See `tools/README.md`.

## Compatibility

The frontend uses Decky's legacy IIFE format, for Decky Loader builds that evaluate `frontend_bundle` rather than loading ES modules.

The backend runs as root, because direct TDP and GPD fan control require it on this hardware.
