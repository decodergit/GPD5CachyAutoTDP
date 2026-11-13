## 3.7.0

Redesigned panel: less text, the important things first.

- **Summary on top:** three tiles — FPS (green / amber / red against the goal, with the goal underneath), TDP and temperature — and one status line with a coloured dot: holding the target, raising TDP, lowering TDP, looking for the lowest TDP, short at the TDP limit, high-load boost, waiting for FPS, Auto TDP off.
- **Last-minute chart** of FPS and TDP with the goal as a dashed line. The history is kept by the backend, so it does not reset when the menu is reopened.
- **Game, display mode and working levels** in one line under the summary.
- Main controls first: Plugin enabled, Auto TDP, Target FPS. **TDP limits** (min, max, start TDP), **More settings** (high-load boost and threshold, poll interval, MangoHud overlay, language) and **Diagnostics** (build, backend, search state, loads, FPS source, fan controller) are collapsed; they stay as left while the plugin is loaded.
- **Fan section:** the curve chart with one caption (°C · % · rpm) instead of five rows.
- The MangoHud / FPS-limit note is shown only when there is no FPS; errors are shown as a banner at the very top.
- Shorter descriptions under toggles and sliders.
- **Language:** one selector (Auto / English / Русский) instead of two toggles. *Auto* follows the Steam language and is the default for new configs; existing configs keep their choice.
- Build row shows 3.7.0.

## 3.6.0

- **Working TDP levels are kept per display mode.** The same game needs different power handheld on the built-in 2K screen and docked on a 2K or 4K monitor. Levels are now stored per game *and* display mode, e.g. `steam:1091500@handheld-1920x1080`, `@external-2560x1440`, `@external-3840x2160`, so a menu exit on the built-in screen no longer jumps to the 4K level (or the other way round).
- The display mode comes from `/sys/class/drm`: which outputs are enabled (built-in eDP or external DP/HDMI) and their native resolution. Any enabled external output means docked; with several, the largest one counts.
- **Dock / undock mid-game:** when the mode changes and that mode already has saved levels, TDP goes straight to its typical level (median of recent levels) instead of waiting for an FPS drop or a long search down. In simulation, docking from 35 W to a 4K screen that needs 68 W and undocking back caused no FPS drop at all.
- The FPS section shows the display mode next to the game.
- Levels saved by 3.4.0–3.5.0 (keyed by game only) are not reused: the mode they were learned in is unknown.
- Build row shows 3.6.0.

## 3.5.0

- **RyzenAdj ships with the plugin.** `bin/ryzenadj` (RyzenAdj v0.18.0, the same file PowerControl v3.15.1 ships) is now in the repository and in the Decky archive, so PowerControl is no longer needed, not even for the first launch. RyzenAdj stays under LGPL-3.0-or-later: the license texts are in `bin/licenses/`, the source link and checksum in `bin/README.txt` and `THIRD_PARTY_NOTICES.md`.
- Decky unpacks archives with Python, which drops the executable bit. The plugin and `tdp_gui.py` now restore it on `bin/ryzenadj` at start. The archive stores `ryzenadj` as 755 and everything else as 644.
- If `bin/ryzenadj` is missing (an old installation), the plugin still copies it from PowerControl.
- **Fan curve as a graph.** The panel shows the curve as a chart (temperature 20–110 °C, speed 0–100 %) with a marker for the current temperature and fan speed. **Edit curve** opens an editor: drag a point to move it, tap empty space to add one; dragging up lifts the points to the right and dragging down lowers the points to the left, so the curve never decreases. A selected point can also be moved with sliders and the ◀/▶ buttons, so the editor works with a gamepad. Delete point, Reset to default, Save and Cancel are in the same window. Replaces the list of per-point sliders.
- Build row shows 3.5.0.

## 3.4.0

- **Fast return after menus.** A menu needs ~10 W, the location ~35 W: when the menu closed, FPS used to stay far below the target for 3–8 s while TDP climbed back. In simulation of the same switch the hard drop (FPS below goal − 4) is now 1–2 s instead of 7–8 s, with no overshoot.
- **No smoothing lag on drops.** A sharp drop (latest reading below goal − 4 fps) is acted on at once, instead of waiting for the 4 s average. A mild deficit counts only readings taken after the last TDP change, so the controller no longer keeps raising after a jump on frames from the old level. Lowering still requires both the long average and the latest reading to show a surplus.
- **Working levels per game.** TDP levels where FPS held near the target for 8 s are remembered and saved per game in `game_stats.json` (game detected from Steam's `SteamLaunch AppId=…` process; anything else shares one entry). On a sharp drop TDP jumps straight to the median remembered level above the current one, capped by an FPS-based estimate (FPS ∝ W^0.9, ×1.5) so a loading screen cannot send it to the maximum. The usual search then trims it down if the scene is lighter.
- **Fixed:** once a plateau had been found, raises were limited to 2 W at every level, even far below that plateau. The small step now applies only near or above the learned ceiling.
- **Fixed:** the raise interval was compared exactly, so timer jitter could skip every second poll. It now has a 10 % tolerance.
- The FPS section shows the detected game and its working TDP levels.
- `tools/simulate_scene_switch.py`: location → menu → location simulation on the real controller.
- Build row shows 3.4.0.

## 3.3.0

- **Plugin enabled switch** is now the first row of the plugin. When it is off, the plugin writes nothing: Auto TDP stops and the fan is handed back to the firmware. The other sections are hidden. The switch is saved as `plugin_enabled` and survives restarts.
- **`tdp_gui.py` pauses the plugin while it is open.** The window writes its PID to `/run/gpd5cachyautotdp/gui.pid`; the plugin checks it every second, stops Auto TDP and the fan curve, and reports back in `plugin.json`. The window applies its own limit and fan mode only after that report (or after 8 s if the plugin does not answer). When the window closes, or crashes, the plugin resumes its saved state. A stale PID that does not belong to `tdp_gui.py` is ignored.
- While paused or switched off, the plugin refuses `start_monitor`, `set_tdp`, `set_fan_speed` and `enable_fan_control`, and does not reset the TDP on unload.
- **Plugin icon**: a chip with a lightning bolt instead of the ⚡ emoji. It follows the Decky theme colour (`currentColor`). The drawing is also in `assets/icon.svg`.
- `tools/build_release.py` builds the Decky archive into `release/` (ignored by git): it checks that the versions match, rebuilds `dist/index.js` and packs the plugin folder.
- Build row shows 3.3.0.

## 3.2.2

- `tdp_gui.py`: the limit is applied when the slider is released (mouse or arrow keys), not while dragging.
- `tdp_gui.py`: the chosen limit is rewritten every 5 seconds, so a firmware or other tool reset is corrected. Nothing is written until a limit is chosen.
- `tdp_gui.py`: the “Apply” and “Read from system” buttons are removed.
- `tdp_gui.py`: if not started as root, it asks for the sudo password in a dialog, checks it with `sudo -S -v` (the password is passed on stdin, never on the command line), then restarts itself with `sudo -n env DISPLAY=… XAUTHORITY=…`.
- `tdp_gui.py`: fan control. Modes “Auto (firmware)”, “Curve” (the backend fan curve) and “Manual” (0–100 % slider, rewritten every 5 seconds). The window shows temperature, fan speed and RPM. Closing the window hands the fan back to the firmware.
- `tdp_gui.py`: fixed the layout: separators were placed on rows already used by labels and crossed the text. The window no longer crashes when no fan is found, and fan status no longer eats the first status line.
- `tdp_gui.py`: settings (TDP limit, fan mode, manual fan speed) are saved to `~/.config/gpd5-tdp-gui.json` of the user who started the window and applied on the next start.
- `tdp_gui.py`: the sudo password is asked only the first time and when the saved one stops working. It is kept in the system keyring (Secret Service via `secret-tool`), never in a file. Without `secret-tool` it is asked every time.
- Build row shows 3.2.2.

## 3.2.1

- `tdp_gui.py` is part of the project and is included in both archives: a Tk desktop window with a live chip power indicator (from the powercap/RAPL energy counter, shown as “no data” when the counter is absent) and a 5–80 W limit slider. It lets you change the limit without switching to Big Picture. Turn Auto TDP off first, otherwise the plugin keeps rewriting the limit.
- The Decky archive previously left the desktop tool out; it is now included.
- Build row shows 3.2.1.

## 3.2.0

- **Fixed fan curve editor layout.** Temperature and speed sliders for one point were placed in a single row, so the section looked like duplicated points. Now all temperature sliders come first, then all speed sliders, each point numbered once.
- **Duplicates in the stored curve are merged.** `curveFromConfig` now collapses several values for the same temperature (e.g. `"70"` and `"70.0"`, or a hand-edited config) into one point, keeping the higher speed. Invalid entries are dropped instead of rendering as extra points.
- **Saving merges duplicates too**, so a curve can no longer be written back with two values for one temperature.
- **Reset already replaced the curve** rather than adding points; this is now covered by tests (3 points → exactly 9, repeated resets stay at 9).
- Build row shows 3.2.0.

## 3.1.0

- **TDP now ramps up proportionally instead of in fixed steps.** The step depends on two values: the width of the available TDP range (max − min) and the relative FPS shortfall. On a 65 W range with a 12 fps shortfall the step is about 6.5 W, with 4 fps about 2 W, with 2 fps about 1 W. A narrow range gives proportionally smaller steps, so the same rule works for any limits.
- The step is capped at half the range, and while a plateau check is open at 12 % of the range, so a single window cannot run far above the working level.
- **Plateau detection is now two-strike.** One failed check is often just noise (±1.5 fps over two or three samples easily crosses the threshold). The cap is applied only after two failures in a row, which removed the cases where the TDP stalled below the level that still delivers frames.
- **Plateau requires a shortfall.** The cap is not applied when the raise already brought FPS to the target: that is a reached result, not a plateau.
- **Learned ceiling.** Once a plateau has been found, later raises above that level are small (2 W) and rare (10 s), so the controller does not spend power above a level already shown to be useless.
- Simulation, 25 W start, target requiring 44 W: reaching working TDP takes 4–6 s at noise ±0, ±1.5 and ±3 fps. In 3.0.0 two runs out of eight took 67 s because of a false plateau.
- Build row shows 3.1.0.

## 3.0.0

- **FPS ramps up much faster.** Poll interval now defaults to 1 s instead of 3 s, and the raise interval follows the poll interval instead of being fixed at 2 s. In simulation, reaching the target from 25 W took 90 s before and 9 s now.
- **Fixed a false plateau lock.** The plateau check compared the FPS after a raise with the FPS recorded at the moment of the raise, which still belonged to the old TDP. When polls were infrequent the comparison window was also too short, so the plateau fired on the first raise and TDP stuck at the bottom. The check now compares a stable average before the raise with a stable average at the end of the window, and waits for at least two samples.
- **Fixed the FPS reader cost.** Each poll read the whole MangoHud CSV three times, once per metric; `stats()` read it a fourth time. On a 2 MB log that was 240 ms per poll, so a shorter interval would have made things worse. Now the header and a 64 KB tail are read once for all metrics: 2.7 ms regardless of file size, 9–88× faster. `stats()` no longer re-reads.
- **New Poll interval slider** (0.5–5 s) in the interface, saved as `check_interval_sec`. The raise interval and the plateau window follow it automatically.
- Build row shows 3.0.0.

## 2.7.0

- `dist/index.js` is now built from `src` with rollup instead of being edited by hand. The manual copy could drift from the source; that risk is gone.
- Fixed `package.json`: `@decky/ui` was pinned to `^2.0.0`, a version that does not exist, so `npm install` failed. Now `^4.15.1`.
- Fixed `tsconfig.json`: `jsx` was `react-jsx`, which emits calls to a JSX runtime module. Decky passes React itself (`SP_REACT`), so the bundle now uses the classic `React.createElement`.
- Fixed the bundle footer so the script value is the plugin object, as the legacy Decky loader expects.
- Added `tools/collect_metrics.py` and `tools/analyze_metrics.py` for on-device checks: TDP, FPS, temperature, fan speed, and an analysis of how fast TDP falls, how often it changes, and whether lowering the TDP causes FPS drops. Nothing in the system is modified.
- Build row shows 2.7.0.

## 2.6.0

- Fan curve editor in the interface: each point has a temperature and a speed slider, points can be added and removed, and the curve can be saved or reset. A rejected curve shows the backend reason instead of a bare failure.
- TDP search status in the interface: search state, the lowest level that holds the goal, the highest level that does not, and the number of tries.
- Initialization errors are collected by the backend and shown in the Status section, instead of only being written to the log.
- Dictionary extended to 87 keys per language; English and Russian stay in sync.
- Build row shows 2.6.0.

## 2.5.0

- Fan controller: hysteresis (the curve is recalculated only after the temperature moved more than 2 °C), a 2 % PWM dead band (no sysfs writes for smaller changes), a ramp limit (+25 %/s up, −10 %/s down), a minimum of 18 % while control is on, the maximum over all found temperature sensors, and a 1 s poll that writes only on change.
- Fan feed-forward: a TDP increase raises the target fan speed by 1.5 % per watt for 8 s (capped at 30 %). TDP decreases add nothing.
- `set_fan_curve` and `reset_fan_curve` return `{ok, error}`; a rejected curve reports the reason.
- Tests for each fan requirement on a fake hwmon.

## 2.3.0

- Removed the Active CPU cores feature completely: the slider, the status text under it, core evacuation, the IRQ and thread moving code, and the saved `active_cores` setting.
- Removed backend modules `cpu_topology.py` and `core_evacuation.py` and the `set_active_cores` RPC.
- One remaining action at startup and on unload: all CPUs are switched back online (backend/cpu_online.py). This restores the full core count if an earlier version left cores disabled. CPU 0 is never touched.
- Status no longer shows "Core evacuation". The interface translations for core control were removed.
- Build row shows 2.3.0.

## 2.2.0

- Interface language: English and Русский. The choice is at the bottom of the screen (Language section). It is saved in config.json as `language` ("en" or "ru") and restored on startup.
- All interface texts come from one dictionary (`src/i18n.ts`); the English and Russian sets have the same keys.
- Backend: `set_language` RPC accepts only "en" or "ru". `validate_config` rejects other values. Old configs without `language` default to English.
- Build row shows 2.2.0.

## 2.1.1

- Active CPU cores: the slider now stays where you set it while the change runs. The change runs in the background; the RPC returns at once. Under the slider the status is shown: stage, current item, result or error.
- Stage text: "включение оставляемых ядер", "вытеснение задач и IRQ", "отключение ядер", with progress counters.
- Evacuation: IRQ write errors no longer block core switch-off. Some IRQs are managed by the kernel and it moves them itself. Threads that already exited (ESRCH) are not counted as stuck.
- Evacuation still refuses switch-off if a user thread is pinned only to the cores being disabled. The reason is shown in the status.
- The saved core count is written only after a successful change.
- FPS hold controller (backend/fps_hold_controller.py) replaces the step logic in the monitor:
  - shortfall (below the goal): TDP is raised in 1-3 W steps, at most once per 2 s;
  - surplus: TDP is lowered by 1 W only after the surplus has lasted 10 s, at most once per 8 s; a single frame above the goal does not lower TDP;
  - plateau: after a raise, if smoothed FPS did not grow by 1 fps within 6 s, the current TDP becomes a ceiling for 60 s. TDP is not raised above the ceiling while FPS is short;
  - when the data is missing, TDP is not changed.
- Fix: the Active CPU cores hook was placed after early returns in the UI; it now runs first.
- Build row shows 2.1.1.

## 2.1.0

- Effective FPS goal: the controller aims at the user's target FPS + 2. The Target FPS slider keeps the user's value; the goal is shown as "Effective FPS goal".
- FPS/TDP model (backend/fps_tdp_model.py): after each FPS-driven TDP increase, the model measures the average FPS over the window. If the FPS gain is below 1 fps, TDP is capped at that level for 30 s. The cap is re-evaluated after it expires. TDP decreases are never blocked.
- The CPU load boost is not gated by the model: it exists for shader compilation, where FPS does not rise.
- Core evacuation (backend/core_evacuation.py): before a physical core is switched off, IRQs are moved to the remaining cores and user threads are moved off the disabled CPUs with sched_setaffinity. Kernel threads (ksoftirqd, kworker) are not moved; the kernel handles them.
- A core is switched off only if evacuation completes without stuck threads. Otherwise the request fails and the UI shows the number of stuck threads. Increasing the core count does not run evacuation.
- The active core count is saved to config only when it was actually applied.
- Status shows "Effective FPS goal", "TDP decision" and "Core evacuation".
- Build row shows 2.1.0.

## 2.0.0

- Minimum active physical cores lowered from 4 to 2. The UI, backend and documentation use the same value.
- Maximum TDP raised from 55 W to 80 W. Affects the Maximum TDP slider, the Start TDP slider, backend clamping (`tdp_controller`, `monitor`), config defaults and validation.
- Added active CPU core control. The new "Active CPU cores" slider disables whole physical cores (both SMT threads together), so Hyper-Threading stays enabled on every remaining core.
- The core count maximum is read from the system at startup (`possible` and `thread_siblings_list`), not hard-coded.
- CPU 0 is never taken offline.
- The selected core count is saved in `config.json` and reapplied on startup. Plugin unload restores all CPUs online.
- Auto TDP switch moved to the top of the screen, so the plugin can be scrolled from top to bottom with the controller. MangoHud settings stay at the bottom.
- Startup now reads the CPU topology before applying the saved core count.
- Existing configs written by 1.x had `max_tdp: 55`. On load, a 1.x config with 55 W is migrated to 80 W and saved, so the slider reflects the new default. Values changed by the user in 2.0.0 are kept.
- The UI caps the Maximum TDP slider at 80 W even if the config contains a higher value.
- The Status section now shows a `Build` row with the backend version. If it reads "старый backend", the installed plugin is from before this change.

## 1.3.0

- Fixed legacy Decky RPC response handling, including `get_config`.
- Fixed startup: `_main` was invoked without a bound instance (`Plugin._main() missing 'self'`), so the watchdog and config were never created. Plugin state now lives in a module-level object.
- Startup watchdog moved to a module-level task; it restarts initialization if the monitor stays in `waiting` for more than 10 seconds (30-second cooldown).
- RPC methods no longer leak backend exceptions to Decky: failures are logged and replaced with safe defaults.
- A corrupt `config.json` is moved to `config.json.corrupt-<timestamp>` and defaults are written instead of blocking startup.
- The frontend no longer treats a backend `{result: "<error>", success: false}` envelope as configuration; the real error text is shown.
- Serialized TDP backend access and removed `ryzenadj -i` from Strix Halo live telemetry.
- Moved blocking backend calls off the Decky asyncio event loop.
- Added thread-safe, atomic configuration writes.
- Removed per-adjustment config writes from the AutoTDP control loop.
- Debounced live Target FPS / TDP slider changes.
- Serialized TDP backend access and removed `ryzenadj -i` from Strix Halo live telemetry.
- Moved blocking backend calls off the Decky asyncio event loop.
- Added thread-safe, atomic configuration writes.
- Removed per-adjustment config writes from the AutoTDP control loop.
- Debounced live Target FPS / TDP slider changes.


## 1.2.1

- Added a startup watchdog: if AutoTDP remains in `waiting` for more than 10 seconds, the plugin performs a full backend reinitialization.
- Added a 30-second restart cooldown to prevent rapid reinitialization loops.
- The watchdog is cancelled cleanly when Decky unloads the plugin.


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
