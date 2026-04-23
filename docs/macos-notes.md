# macOS Notes

This note describes how the macOS text injection path works and how the app chooses between Accessibility-based insertion and clipboard-based paste.

## Overall model

On macOS, the app treats text insertion as a target-sensitive operation.

The core idea is:

- capture the focused target when recording starts
- preserve or restore focus while recording is in progress
- when transcription finishes, choose an insertion method based on the kind of target that was captured

This behavior spans three main components:

- [recognizer.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/recognizer.py): owns the manual recording lifecycle and hands the final audio clip to the speech provider and injector
- [audio.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/audio.py): captures raw microphone audio into an in-memory buffer
- [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py): captures the macOS target and performs text insertion

## Recording and target capture

When recording starts, the app creates a `ManualAudioRecorder` and also captures the current macOS insertion target.

That target capture happens before the user finishes speaking so the app can later return text to the same place. The captured target is not just the frontmost app name. On macOS it includes:

- the focused Accessibility application object
- the focused window
- the focused UI element
- the frontmost bundle id
- the frontmost app name

The target metadata is represented by `MacOSInjectionTarget` in [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

This is important because different macOS apps expose very different Accessibility surfaces. A browser text box, a Word document, a terminal surface, and a remote desktop client do not behave like the same kind of editable control.

## Focus restoration

The app tries to keep insertion stable by restoring focus twice:

1. shortly after recording starts
2. again immediately before text insertion

The first restoration helps keep the original target active even though the recording indicator and hotkey flow may briefly change attention. The second restoration makes sure the final transcript goes back to the same app, window, and UI element that was active when recording began.

On macOS, focus restoration is implemented in `MacOSTextInjector.restore_target()` and `_restore_focus_target()` in [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

## Accessibility-based insertion

For normal editable controls, the preferred path is direct Accessibility insertion.

This path works by reading and updating standard Accessibility text attributes such as:

- `AXSelectedText`
- `AXSelectedTextRange`
- `AXValue`

The injector attempts to use the most specific operation available:

1. replace selected text if the target exposes a selected-text range
2. replace a selected range inside the current value
3. append to the current value when the control behaves like a standard editable field

This approach is a good fit for apps that expose a conventional editable document or text field through macOS Accessibility APIs.

## Clipboard paste fallback

Not every focused target behaves like a normal editable control. For those cases, the injector falls back to clipboard paste.

The fallback sequence is:

1. copy the transcript to the macOS clipboard with `pbcopy`
2. optionally re-activate the target app
3. send a configured paste shortcut through `osascript` and `System Events`

The paste shortcut is configurable because the correct shortcut depends on the target environment, not just on macOS itself.

## Browser targets

Browser targets usually expose an Accessibility-backed editable element inside a larger browser process.

From the injector's point of view, browsers are still "normal editable controls" as long as the exact focused element is preserved. That is why the macOS path captures the focused UI element instead of relying only on the app identity.

For browser text fields, the preferred behavior is:

- restore the exact focused element
- attempt Accessibility insertion first
- use clipboard paste only if the editable Accessibility path is not available

## Word-style editable applications

Apps such as Word behave more like standard document editors from the injector's point of view.

These apps often expose text ranges and current values in a way that maps cleanly to the Accessibility insertion path. In practice, they are the best match for direct text mutation through `AXSelectedText`, `AXSelectedTextRange`, and `AXValue`.

## Native terminal targets

Terminal apps are different from standard editors. A terminal window is typically a rendered terminal surface connected to a shell or PTY rather than a document-style editable text field.

Because of that, the injector treats terminals as paste-oriented targets. The current macOS implementation recognizes native terminal apps by bundle id and skips the Accessibility insertion path for them.

For native terminal targets, the app:

- restores focus
- keeps the transcript on the clipboard
- uses the paste path instead of mutating an Accessibility text value

The terminal app detection list currently lives in `_TERMINAL_BUNDLE_IDS` in [macos.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/injectors/macos.py).

## Remote desktop targets such as RustDesk

Remote desktop clients are their own category because the locally focused macOS app is the remote desktop client, while the actual text consumer may be a remote terminal or editor.

That means a remote desktop target should not be treated like a standard local editable control. The app captures both bundle id and app name so it can recognize targets such as RustDesk and choose a different insertion strategy.

For RustDesk-style targets, the injector treats the session as a remote paste target:

- Accessibility text mutation is skipped
- the transcript is copied to the macOS clipboard
- the injector sends the configured remote paste shortcut instead of the normal local macOS paste shortcut

This is why the injector distinguishes between:

- the default local paste shortcut, `DICTATION_MACOS_PASTE_SHORTCUT`
- the remote-target paste shortcut, `DICTATION_MACOS_REMOTE_PASTE_SHORTCUT`
- the remote-target match list, `DICTATION_MACOS_REMOTE_PASTE_TARGETS`

With the current defaults, normal local fallback paste uses `command+v`, while RustDesk-like targets use `ctrl+shift+v`.

## Non-activating recording indicator

The recording/transcribing indicator is designed to avoid stealing focus from the real insertion target.

On macOS, this is handled by configuring the Tk window as a non-activating panel. That behavior lives in [recording_indicator.py](/Users/schuang/work/speech-to-text/src/speech_to_text_app/recording_indicator.py).

This component matters because the text injection path depends on preserving the user's original insertion target while the app records and transcribes in the background.

## End-to-end insertion sequence

In practical terms, the macOS flow is:

1. capture the focused app, window, element, bundle id, and app name
2. start recording audio into memory
3. restore the original target after recording begins
4. stop recording and hand the full audio clip to the selected speech provider
5. restore the target again before insertion
6. choose Accessibility insertion or clipboard paste based on the target type
7. inject the final transcript and leave it on the clipboard

## Summary by target class

### Browser text field

- Target model: editable Accessibility control inside a browser process
- Preferred insertion path: direct Accessibility insertion
- Fallback: clipboard paste

### Word-style app

- Target model: standard document or text editor surface
- Preferred insertion path: direct Accessibility insertion
- Fallback: clipboard paste

### Native terminal

- Target model: terminal surface connected to a shell or PTY
- Preferred insertion path: clipboard paste
- Accessibility insertion: skipped

### RustDesk to remote terminal

- Target model: remote desktop client forwarding input to a remote app
- Preferred insertion path: clipboard paste with the remote paste shortcut
- Accessibility insertion: skipped
