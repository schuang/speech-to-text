from __future__ import annotations

import sys

from .devices import InputDevice, usb_input_devices

if sys.platform == "win32":
    from .windows import input_device_name
else:
    from .fallback import input_device_name

__all__ = ["InputDevice", "input_device_name", "usb_input_devices"]
