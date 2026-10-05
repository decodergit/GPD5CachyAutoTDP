# Security and hardware safety

GPD5CachyAutoTDP performs privileged hardware-control operations because GPD WIN 5 TDP and fan interfaces require root access in the target CachyOS Handheld environment.

Do not run multiple TDP/fan controllers simultaneously. In particular, PowerControl must be installed for the first initialization, but deactivated before GPD5CachyAutoTDP is launched.

This project is temporary pending native upstream support and is provided as-is under the MIT License.


## High-load boost

The high-load boost can raise TDP up to the configured Maximum TDP. Keep Maximum TDP at a value appropriate for the device cooling and power adapter. CPU-bound workloads such as shader compilation may intentionally trigger this behavior even when FPS is already at the target.
