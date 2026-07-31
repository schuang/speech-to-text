from __future__ import annotations

import sys

if sys.platform == "win32":
    from .windows import input_device_name
else:
    from .fallback import input_device_name

__all__ = ["input_device_name"]
