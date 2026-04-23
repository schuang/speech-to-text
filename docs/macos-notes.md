# macOS Notes

This app behaves differently on macOS depending on what kind of target is focused when recording starts.

The important distinction is:

- a browser text field is usually an Accessibility-backed editable control inside a larger browser app
- a normal app like Word is also an editable text control, and usually exposes cleaner Accessibility text APIs
- a terminal is not a normal text editor widget; it is typically a terminal surface backed by a shell/PTY, so "set text value" is often the wrong operation
- a remote desktop client such as RustDesk adds another layer: the locally focused app is RustDesk, but the real text consumer may be a remote Linux terminal with its own paste semantics

## High-level flow

When recording starts, the app captures the current macOS insertion target and remembers it for the end of the transcription.

This happens in [recognizer.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/recognizer.py):

- `start_recording()` captures the current target with `injector.capture_target()`
- `restore_target_focus()` can re-focus that target after recording starts
- `_transcribe_and_inject()` sends the final transcript back to `injector.type_text(...)`

On macOS, the injector is [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

The macOS path is intentionally hybrid:

- capture Accessibility context early so the original target can be restored
- prefer Accessibility insertion for normal editable controls
- fall back to clipboard paste for terminal-like or remote-desktop-like targets
- keep the final transcript on the clipboard in every case

## Why browsers were tricky

Browsers had two separate problems.

### 1. `F6` is a browser focus shortcut

`F6` often moves focus to browser chrome, especially the address bar. That means the browser itself was changing focus before insertion even happened.

Fix:

- the macOS default hotkey was changed from `F6` to `ctrl+shift+space`

### 2. Restoring only the app was not enough

Re-activating Safari or Chrome does not guarantee the caret returns to the original text box inside the webpage. If the page field loses focus, browsers often fall back to the address bar.

Fixes:

- the app now captures the focused macOS Accessibility element, not just the app
- after recording starts, it tries to restore that target again so the page field keeps focus
- before insertion, it restores the target again
- for browser-like editable controls, it first tries direct Accessibility text insertion instead of relying only on `Cmd+V`

Relevant code:

- target capture and restore: [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py)
- non-activating overlay window: [recording_indicator.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/recording_indicator.py)

## Why Word worked more easily

Word behaves more like a standard editable document surface from the injector's point of view.

That means these Accessibility operations are more likely to work:

- `AXSelectedText`
- `AXSelectedTextRange`
- `AXValue`

So for Word and similar normal apps, the macOS injector can often:

1. restore the focused element
2. replace the selected text directly, or
3. update the text value directly

This is why the Accessibility-based insertion path is a good fit for Word-like apps.

## Why terminals needed different treatment

A terminal window is not a regular editable text field. It is usually a rendered terminal surface connected to a running shell.

Because of that, Accessibility text mutation is often the wrong tool:

- setting `AXValue` does not necessarily mean "type into the shell"
- replacing `AXSelectedText` does not necessarily send characters to stdin

For terminals, paste is the correct fallback much more often than direct Accessibility text mutation.

Fix:

- Terminal and iTerm are detected by bundle id
- for those apps, the macOS injector skips the Accessibility insertion path
- it restores focus and then goes directly to clipboard paste

Current terminal bundle handling is driven by `_TERMINAL_BUNDLE_IDS` in [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

## Why RustDesk remote terminals needed additional handling

RustDesk looks different from a native terminal even though the user intent is similar.

From macOS, the focused app is RustDesk itself, not the remote terminal. That means the injector cannot treat the target like a normal local browser, Word document, or Terminal.app session.

The failure mode was specific:

- the transcript was copied to the macOS clipboard correctly
- the injector sent the standard macOS paste chord, `Command+V`
- inside a remote Linux terminal shown through RustDesk, that did not trigger terminal paste
- the remote terminal effectively received only `v`
- manually pressing `Ctrl+Shift+V` in the remote session pasted the transcript correctly

That behavior shows why remote desktop sessions need target-specific paste handling. The correct operation is not "paste into the macOS app", but "send the paste shortcut that the remote application expects".

Fix:

- RustDesk targets are detected by frontmost app name or bundle id
- those targets are treated like paste-only surfaces, so the injector skips Accessibility text insertion
- for RustDesk targets, the macOS fallback paste chord defaults to `ctrl+shift+v` instead of `command+v`
- local apps still keep the normal macOS fallback of `command+v`

This logic is implemented in the target-aware paste selection code in [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

## Configurable paste behavior

The remote-desktop handling is configurable because not every remote session uses the same paste shortcut.

Relevant environment variables:

- `DICTATION_MACOS_PASTE_SHORTCUT`: default fallback paste chord for normal local macOS targets
- `DICTATION_MACOS_REMOTE_PASTE_SHORTCUT`: alternate fallback paste chord for detected remote targets such as RustDesk
- `DICTATION_MACOS_REMOTE_PASTE_TARGETS`: comma-separated app names or bundle-id fragments that should use the remote paste shortcut

Current defaults:

- local fallback paste: `command+v`
- remote fallback paste: `ctrl+shift+v`
- remote target match list: `rustdesk`

This keeps the normal macOS behavior unchanged for local apps while allowing remote desktops to use the shortcut expected by the remote environment.

## Floating indicator behavior

The recording/transcribing indicator is intentionally configured as a non-activating macOS window so it does not steal focus from the real target app.

That logic lives in [recording_indicator.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/recording_indicator.py), using the macOS Tk window style with `noActivates`.

## Current insertion strategy on macOS

In practical terms, the app now does this:

1. Capture the focused app/window/element when recording starts.
2. Start recording.
3. Re-focus the original target after recording begins.
4. When transcription finishes, restore the target again.
5. If the target looks like a normal editable control, try direct Accessibility insertion first.
6. If the target is a native terminal, skip direct insertion and use clipboard paste.
7. If the target is a remote desktop target such as RustDesk, skip direct insertion and use the remote paste shortcut instead of the local macOS one.
8. Keep the transcript on the clipboard as backup in all cases.

## Summary by app type

### Browser

- Main risk: browser hotkeys and loss of caret focus inside the webpage
- Best strategy: avoid `F6`, restore exact target, try direct Accessibility insertion first

### Word or similar app

- Main risk: much lower
- Best strategy: direct Accessibility text insertion usually works well

### Terminal

- Main risk: terminal is not a normal editable text field
- Best strategy: skip Accessibility text mutation and use paste after restoring focus

### RustDesk to remote terminal

- Main risk: the frontmost macOS app is RustDesk, but the remote terminal expects Linux terminal paste semantics
- Best strategy: skip Accessibility text mutation, restore the RustDesk target, and send the configured remote paste chord, which defaults to `Ctrl+Shift+V`
