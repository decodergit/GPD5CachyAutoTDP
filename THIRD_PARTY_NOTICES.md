# Third-party notices

GPD5CachyAutoTDP source code is licensed under the MIT License. The third-party
components and software referenced below remain under their respective
upstream licenses.

## RyzenAdj

GPD5CachyAutoTDP uses the RyzenAdj command-line utility for AMD TDP control.
RyzenAdj is licensed under LGPL-3.0-or-later and is developed by FlyGoat and
contributors.

Upstream:
https://github.com/FlyGoat/RyzenAdj

Since 3.5.0 the repository and the plugin archive include the RyzenAdj
v0.18.0 executable as `bin/ryzenadj` (the same file PowerControl v3.15.1
ships). It is distributed unmodified under LGPL-3.0-or-later, separately from
this project's MIT-licensed code. The license texts are in `bin/licenses/`
(`RyzenAdj-LGPL-3.0.txt` and `GPL-3.0.txt`), and the corresponding source code is
available at https://github.com/FlyGoat/RyzenAdj/tree/v0.18.0. The plugin only
runs it as a separate program, and users may replace it with their own build.

## PowerControl

PowerControl is an independent Decky Loader plugin. It is licensed under the
BSD 3-Clause License.

Upstream:
https://github.com/mengmeet/PowerControl

GPD5CachyAutoTDP does **not** redistribute the PowerControl plugin itself.
The bundled `bin/ryzenadj` was taken from PowerControl's distribution; it is
RyzenAdj (see above), not PowerControl code. The fan curve graph is an
independent implementation that follows the same idea as PowerControl's.

## Decky Loader

GPD5CachyAutoTDP is a plugin for Decky Loader and uses its plugin APIs.
GPD5CachyAutoTDP does not redistribute the Decky Loader source code.

Upstream:
https://github.com/SteamDeckHomebrew/decky-loader

## MangoHud

GPD5CachyAutoTDP can interact with the MangoHud/mangoapp runtime provided by
the user's CachyOS Handheld environment. It does not redistribute MangoHud
source code or binaries.

Upstream:
https://github.com/flightlessmango/MangoHud

## Linux GPD fan driver

GPD5CachyAutoTDP accesses the Linux hwmon/sysfs interface exposed by the GPD
fan driver. It does not redistribute the driver source code.

The driver is part of the Linux kernel ecosystem and remains under its
upstream license.

## JavaScript dependencies

JavaScript packages such as Decky API/UI and React are used as external
development/build dependencies. Their upstream licenses remain applicable
to those packages. GPD5CachyAutoTDP does not relicense those dependencies
under the MIT License.
