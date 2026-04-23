from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

try:
    import ApplicationServices as AS
except ImportError:
    class _ApplicationServicesStub:
        kAXErrorSuccess = 0
        kAXFocusedApplicationAttribute = "AXFocusedApplication"
        kAXFocusedUIElementAttribute = "AXFocusedUIElement"
        kAXRaiseAction = "AXRaise"
        kAXFocusedAttribute = "AXFocused"
        kAXSelectedTextRangeAttribute = "AXSelectedTextRange"
        kAXSelectedTextAttribute = "AXSelectedText"
        kAXValueAttribute = "AXValue"
        kAXValueCFRangeType = "AXValueCFRangeType"

        class CFRange:
            def __init__(self, location: int = 0, length: int = 0) -> None:
                self.location = location
                self.length = length

        @staticmethod
        def AXUIElementCreateSystemWide() -> None:
            return None

        @staticmethod
        def AXUIElementCopyAttributeValue(_element, _attribute, _unused) -> tuple[int, None]:
            return (1, None)

        @staticmethod
        def AXUIElementPerformAction(_element, _action) -> int:
            return 1

        @staticmethod
        def AXUIElementSetAttributeValue(_element, _attribute, _value) -> int:
            return 1

        @staticmethod
        def AXValueGetValue(_value, _value_type, _unused) -> tuple[bool, None]:
            return (False, None)

    AS = _ApplicationServicesStub()

from .base import TextInjectorError


_TERMINAL_BUNDLE_IDS = {
    "com.apple.Terminal",
    "com.googlecode.iterm2",
}
_DEFAULT_PASTE_SHORTCUT = "command+v"
_DEFAULT_REMOTE_PASTE_SHORTCUT = "ctrl+shift+v"
_DEFAULT_REMOTE_PASTE_TARGETS = ("rustdesk",)
_MODIFIER_ALIASES = {
    "alt": "option down",
    "cmd": "command down",
    "command": "command down",
    "control": "control down",
    "ctrl": "control down",
    "option": "option down",
    "shift": "shift down",
}
_SPECIAL_KEY_CODES = {
    "enter": 36,
    "return": 36,
    "tab": 48,
}


@dataclass(frozen=True)
class MacOSInjectionTarget:
    app: object | None
    window: object | None
    element: object | None
    bundle_id: str | None
    app_name: str | None


class MacOSTextInjector:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        del delay_seconds
        self._default_paste_shortcut = (
            os.getenv("DICTATION_MACOS_PASTE_SHORTCUT", "").strip()
            or _DEFAULT_PASTE_SHORTCUT
        )
        self._remote_paste_shortcut = (
            os.getenv("DICTATION_MACOS_REMOTE_PASTE_SHORTCUT", "").strip()
            or _DEFAULT_REMOTE_PASTE_SHORTCUT
        )
        self._remote_paste_targets = self._load_remote_paste_targets()
        if sys.platform == "darwin":
            self._require_tool("osascript")
            self._require_tool("pbcopy")

    def capture_target(self) -> MacOSInjectionTarget | None:
        system = AS.AXUIElementCreateSystemWide()
        app = self._copy_ax_value(system, AS.kAXFocusedApplicationAttribute)
        element = self._copy_ax_value(system, AS.kAXFocusedUIElementAttribute)
        window = self._copy_ax_value(app, "AXFocusedWindow") if app is not None else None
        app_name = self._frontmost_app_name()
        bundle_id = self._frontmost_bundle_id()

        if app is None and element is None and bundle_id is None and app_name is None:
            return None

        return MacOSInjectionTarget(
            app=app,
            window=window,
            element=element,
            bundle_id=bundle_id,
            app_name=app_name,
        )

    def restore_target(self, target: object | None) -> None:
        if isinstance(target, MacOSInjectionTarget):
            self._restore_focus_target(target)

    def type_text(self, text: str, target: object | None = None) -> None:
        if not text:
            return

        self._copy_to_clipboard(text)

        macos_target = target if isinstance(target, MacOSInjectionTarget) else None
        if macos_target is not None:
            self._restore_focus_target(macos_target)
            if self._should_use_ax_insertion(macos_target) and self._insert_text_into_target(
                text,
                macos_target,
            ):
                return

        target_bundle_id = macos_target.bundle_id if macos_target is not None else None
        current_bundle_id = self._frontmost_bundle_id()
        should_activate_target = bool(
            target_bundle_id and target_bundle_id != current_bundle_id
        )
        self._paste_clipboard(
            target_bundle_id if should_activate_target else None,
            shortcut=self._paste_shortcut_for_target(macos_target),
        )

    def _should_use_ax_insertion(self, target: MacOSInjectionTarget) -> bool:
        bundle_id = (target.bundle_id or "").strip()
        return bundle_id not in _TERMINAL_BUNDLE_IDS and not self._is_remote_paste_target(
            target
        )

    def _require_tool(self, tool_name: str) -> None:
        if shutil.which(tool_name):
            return
        raise TextInjectorError(f"macOS text injection requires `{tool_name}`.")

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as error:
            raise TextInjectorError("macOS text injection requires `pbcopy`.") from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)
            raise TextInjectorError(message) from error

    def _frontmost_app_name(self) -> str | None:
        script = (
            'tell application "System Events"\n'
            '    try\n'
            '        return name of first application process whose frontmost is true\n'
            '    on error\n'
            '        return ""\n'
            '    end try\n'
            "end tell"
        )
        return self._run_osascript_text(script)

    def _frontmost_bundle_id(self) -> str | None:
        script = (
            'tell application "System Events"\n'
            '    try\n'
            '        return bundle identifier of first application process whose frontmost is true\n'
            '    on error\n'
            '        return ""\n'
            '    end try\n'
            "end tell"
        )
        return self._run_osascript_text(script)

    def _run_osascript_text(self, script: str) -> str | None:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

        target = result.stdout.strip()
        return target or None

    def _load_remote_paste_targets(self) -> tuple[str, ...]:
        configured_targets = os.getenv("DICTATION_MACOS_REMOTE_PASTE_TARGETS")
        if configured_targets is None:
            return _DEFAULT_REMOTE_PASTE_TARGETS
        return tuple(
            normalized_target
            for raw_target in configured_targets.split(",")
            if (normalized_target := raw_target.strip().lower())
        )

    def _copy_ax_value(self, element: object | None, attribute: str) -> object | None:
        if element is None:
            return None

        try:
            error_code, value = AS.AXUIElementCopyAttributeValue(element, attribute, None)
        except Exception:  # noqa: BLE001
            return None

        if error_code != AS.kAXErrorSuccess:
            return None
        return value

    def _restore_focus_target(self, target: MacOSInjectionTarget) -> None:
        if target.app is not None:
            try:
                AS.AXUIElementPerformAction(target.app, AS.kAXRaiseAction)
            except Exception:  # noqa: BLE001
                pass

        if target.window is not None:
            try:
                AS.AXUIElementSetAttributeValue(target.window, "AXMain", True)
            except Exception:  # noqa: BLE001
                pass
            try:
                AS.AXUIElementPerformAction(target.window, AS.kAXRaiseAction)
            except Exception:  # noqa: BLE001
                pass

        if target.element is not None:
            try:
                AS.AXUIElementSetAttributeValue(
                    target.element,
                    AS.kAXFocusedAttribute,
                    True,
                )
            except Exception:  # noqa: BLE001
                pass

    def _insert_text_into_target(self, text: str, target: MacOSInjectionTarget) -> bool:
        element = target.element
        if element is None:
            return False

        selected_range = self._copy_ax_value(element, AS.kAXSelectedTextRangeAttribute)
        current_value = self._copy_ax_value(element, AS.kAXValueAttribute)

        if selected_range is not None and self._set_ax_value(
            element,
            AS.kAXSelectedTextAttribute,
            text,
        ):
            return True

        if isinstance(current_value, str) and selected_range is not None:
            insertion = self._replace_selected_range(current_value, selected_range, text)
            if insertion is not None:
                return self._set_ax_value(element, AS.kAXValueAttribute, insertion)

        if isinstance(current_value, str):
            return self._set_ax_value(element, AS.kAXValueAttribute, current_value + text)

        return False

    def _replace_selected_range(
        self,
        current_value: str,
        selected_range_value: object,
        inserted_text: str,
    ) -> str | None:
        try:
            success, selected_range = AS.AXValueGetValue(
                selected_range_value,
                AS.kAXValueCFRangeType,
                None,
            )
        except Exception:  # noqa: BLE001
            return None

        if not success:
            return None

        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start, length = selected_range
        elif isinstance(selected_range, AS.CFRange):
            start = selected_range.location
            length = selected_range.length
        else:
            return None

        start = max(0, int(start))
        length = max(0, int(length))
        end = min(len(current_value), start + length)
        if start > len(current_value):
            start = len(current_value)

        return f"{current_value[:start]}{inserted_text}{current_value[end:]}"

    def _set_ax_value(self, element: object, attribute: str, value: object) -> bool:
        try:
            error_code = AS.AXUIElementSetAttributeValue(element, attribute, value)
        except Exception:  # noqa: BLE001
            return False
        return error_code == AS.kAXErrorSuccess

    def _paste_shortcut_for_target(
        self,
        target: MacOSInjectionTarget | None,
    ) -> str:
        if target is None or not self._is_remote_paste_target(target):
            return self._default_paste_shortcut
        return self._remote_paste_shortcut

    def _is_remote_paste_target(self, target: MacOSInjectionTarget) -> bool:
        if not self._remote_paste_targets:
            return False

        candidates = [
            (target.bundle_id or "").strip().lower(),
            (target.app_name or "").strip().lower(),
        ]
        return any(
            configured_target in candidate
            for configured_target in self._remote_paste_targets
            for candidate in candidates
            if candidate
        )

    def _shortcut_to_applescript(self, shortcut: str) -> str:
        tokens = [token.strip().lower() for token in shortcut.split("+") if token.strip()]
        if not tokens:
            raise TextInjectorError("macOS paste shortcut cannot be empty.")

        key_token = tokens[-1]
        modifier_tokens = tokens[:-1]
        modifiers: list[str] = []

        for modifier_token in modifier_tokens:
            applescript_modifier = _MODIFIER_ALIASES.get(modifier_token)
            if applescript_modifier is None:
                raise TextInjectorError(
                    f"Unsupported macOS paste shortcut modifier: {modifier_token}"
                )
            modifiers.append(applescript_modifier)

        if len(key_token) == 1:
            escaped_key = key_token.replace("\\", "\\\\").replace('"', '\\"')
            keystroke_command = f'keystroke "{escaped_key}"'
        elif key_token == "space":
            keystroke_command = 'keystroke " "'
        elif key_token in _SPECIAL_KEY_CODES:
            keystroke_command = f"key code {_SPECIAL_KEY_CODES[key_token]}"
        else:
            raise TextInjectorError(f"Unsupported macOS paste shortcut key: {key_token}")

        if not modifiers:
            return keystroke_command
        return f"{keystroke_command} using {{{', '.join(modifiers)}}}"

    def _paste_clipboard(
        self,
        target_bundle_id: str | None,
        shortcut: str | None = None,
    ) -> None:
        paste_shortcut = shortcut or self._default_paste_shortcut
        shortcut_script = self._shortcut_to_applescript(paste_shortcut)
        script_lines = []
        if target_bundle_id:
            escaped_bundle_id = target_bundle_id.replace('"', '\\"')
            script_lines.append(f'tell application id "{escaped_bundle_id}" to activate')
            script_lines.append("delay 0.05")
        script_lines.extend(
            [
                'tell application "System Events"',
                f"    {shortcut_script}",
                "end tell",
            ]
        )
        script = "\n".join(script_lines)
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as error:
            raise TextInjectorError("macOS text injection requires `osascript`.") from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)
            raise TextInjectorError(
                "macOS text injection failed. Grant Accessibility access to Terminal "
                f"or your Python app. Details: {message}"
            ) from error
