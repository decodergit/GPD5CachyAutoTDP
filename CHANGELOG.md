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
