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

The GPD5CachyAutoTDP source repository does **not** distribute the RyzenAdj
binary. On first launch, the plugin may copy an existing `ryzenadj`
executable supplied by the user's installed PowerControl installation into
the plugin's local directory for subsequent use. That executable remains
subject to its original license.

## PowerControl

PowerControl is an independent Decky Loader plugin. It is licensed under the
BSD 3-Clause License.

Upstream:
https://github.com/mengmeet/PowerControl

GPD5CachyAutoTDP does **not** redistribute the PowerControl plugin itself.
It may use an existing `ryzenadj` executable supplied by a user's PowerControl
installation during first-launch initialization.

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
