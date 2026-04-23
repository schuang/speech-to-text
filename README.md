# Speech-To-Text Dictation App

This project is a small desktop app written in Python. It records your speech between explicit manual start and stop actions, sends the captured utterance to a speech-to-text provider, pastes the finalized transcript into whichever app is currently focused, and leaves the transcript on the clipboard.

## What It Does

- Uses your local microphone as the audio source.
- Uses explicit manual start/stop recording instead of silence-based auto-stop.
- Supports global hotkeys on macOS and Windows.
- Shows a small Windows recording meter while audio is being captured.
- Supports Google Cloud Speech-to-Text V2, OpenAI transcription models, and Ollama-hosted Gemma 4 transcription.
- Detects the active provider from your environment.
- Shows finalized transcripts in a local control window.
- Pastes final transcript text into the active application, such as a terminal, VS Code, LibreOffice, Word, or a browser text field.
- Copies the finalized transcript to the clipboard.

## Requirements

- Windows, Linux, or macOS
- Python 3.11+ installed and available on `PATH`
- For GCP mode: a Google Cloud project with Speech-to-Text enabled plus local auth
- For OpenAI mode: an `OPENAI_API_KEY`
- For Ollama mode: an `OLLAMA_BASE_URL` that points to a reachable Ollama server
- For Linux text injection:
  - `xdotool` on X11, or
  - `wtype` on Wayland
- For Linux audio capture with `sounddevice`: PortAudio must be installed at the system level
- For macOS text injection: grant Accessibility access to your terminal app or Python app
- For macOS global hotkeys: Accessibility access is also required
- For macOS remote terminals in RustDesk: the app now uses `Ctrl+Shift+V` by default when the focused target is RustDesk. Override with `DICTATION_MACOS_REMOTE_PASTE_SHORTCUT` if your remote terminal expects a different paste chord.

## Setup

1. Install Python.
2. Create the project virtual environment:

   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment before installing or running anything in this project.

   On Windows:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   On Linux:

   ```bash
   source .venv/bin/activate
   ```

   On macOS:

   ```bash
   source .venv/bin/activate
   ```

4. Install dependencies from the activated virtual environment:

   ```powershell
   pip install -e .
   ```

   On Ubuntu or Debian-based Linux systems, install the native runtime dependencies first:

   ```bash
   sudo apt update
   sudo apt install -y libportaudio2 python3-tk xdotool wtype
   ```

   On macOS, install Tkinter and audio dependencies through your Python distribution as needed, then grant Accessibility access before testing text injection.

5. Configure the provider you want to use.

   For Google Cloud:

   ```powershell
   gcloud auth application-default login
   ```

   Or set a service account key path:

   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
   ```

6. Set your provider-specific environment.

   Provider detection works like this:

   - If `SPEECH_PROVIDER` is set to `gcp`, `openai`, or `ollama`, the app uses that value.
   - Otherwise, if `OPENAI_API_KEY` is set, the app uses OpenAI.
   - Otherwise, if `OLLAMA_BASE_URL` is set, the app uses Ollama.
   - Otherwise, the app defaults to Google Cloud.

   For Google Cloud:

   ```powershell
   $env:SPEECH_PROVIDER="gcp"
   $env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   ```

   Optional: set the Speech-to-Text location. `chirp_3` should use a supported regional location such as `us`.

   ```powershell
   $env:GOOGLE_CLOUD_LOCATION="us"
   ```

   Optional: set the global hotkey. On macOS the default is `ctrl+shift+space`. On Windows the default is `ctrl+alt+space`. Global hotkeys are currently supported on Windows and macOS.

   ```powershell
   $env:DICTATION_HOTKEY="ctrl+shift+space"
   ```

   Optional on macOS: override the local paste chord or the RustDesk remote paste chord.

   ```bash
   export DICTATION_MACOS_PASTE_SHORTCUT="command+v"
   export DICTATION_MACOS_REMOTE_PASTE_SHORTCUT="ctrl+shift+v"
   export DICTATION_MACOS_REMOTE_PASTE_TARGETS="RustDesk"
   ```

   For OpenAI:

   ```powershell
   $env:SPEECH_PROVIDER="openai"
   $env:OPENAI_API_KEY="your-openai-api-key"
   ```

   For Ollama:

   ```powershell
   $env:SPEECH_PROVIDER="ollama"
   $env:OLLAMA_BASE_URL="http://your-ollama-host:11434"
   $env:OLLAMA_MODEL="gemma4:default"
   ```

## Run

Set your provider environment in the current shell, then start the app.

Windows:

```powershell
$env:SPEECH_PROVIDER="gcp"
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
.\run.ps1
```

Linux:

```bash
export SPEECH_PROVIDER="gcp"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run.sh
```

macOS:

```bash
export SPEECH_PROVIDER="gcp"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run.sh
```

You can also set the location if you want to override the default `us` region:

```powershell
$env:GOOGLE_CLOUD_LOCATION="us"
.\run.ps1
```

If you prefer not to set environment variables, you can pass the project directly on Windows:

```powershell
.\run.ps1 -ProjectId your-gcp-project-id
```

OpenAI example:

```powershell
$env:SPEECH_PROVIDER="openai"
$env:OPENAI_API_KEY="your-openai-api-key"
.\run.ps1
```

Ollama example:

```powershell
$env:SPEECH_PROVIDER="ollama"
$env:OLLAMA_BASE_URL="http://your-ollama-host:11434"
$env:OLLAMA_MODEL="gemma4:default"
.\run.ps1
```

Linux OpenAI example:

```bash
export SPEECH_PROVIDER="openai"
export OPENAI_API_KEY="your-openai-api-key"
./run.sh
```

macOS OpenAI example:

```bash
export SPEECH_PROVIDER="openai"
export OPENAI_API_KEY="your-openai-api-key"
./run.sh
```

OpenAI with provider auto-detection:

```bash
export OPENAI_API_KEY="your-openai-api-key"
./run.sh
```

Linux Ollama example:

```bash
export SPEECH_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://your-ollama-host:11434"
export OLLAMA_MODEL="gemma4:default"
./run.sh
```

Optional location override:

```powershell
.\run.ps1 -Location us
```

Windows smoke test without opening the UI:

```powershell
.\run.ps1 -SmokeTest
```

## How To Use

1. Launch the app.
2. Confirm the detected provider, then review the fields shown for that provider.
3. If the app is using Google Cloud, confirm the project ID and location.
4. If the app is using OpenAI, confirm that `OPENAI_API_KEY` is set in your shell.
5. If the app is using Ollama, confirm that `OLLAMA_BASE_URL` is set in your shell and the model field matches the server model name.
6. Click into the target app where text should appear.
7. Click `Start Recording` or use the global hotkey where supported.
8. Speak your full prompt, including long pauses if needed.
9. Click `Stop And Transcribe`, or press the hotkey again to stop recording, transcribe, and paste into the currently focused app.

The app only injects finalized transcription results. It does not auto-stop on silence. Finalized text is also copied to the clipboard.

## Notes

- The default provider is `gcp`.
- Provider selection comes from `SPEECH_PROVIDER` when set, otherwise the app infers OpenAI when `OPENAI_API_KEY` is present, then Ollama when `OLLAMA_BASE_URL` is present.
- The UI no longer exposes provider editing. It shows only the fields relevant to the detected provider.
- When OpenAI is active, the UI hides Google Cloud project and location fields.
- When Ollama is active, the UI expects `OLLAMA_BASE_URL` from the environment and uses the model field for the Ollama model name.
- When Google Cloud is active, the UI hides OpenAI-specific status rows.
- The default GCP model is `chirp_3`.
- The default OpenAI model is `gpt-4o-mini-transcribe`.
- The default Ollama model is `gemma4:default`, but `OLLAMA_MODEL` overrides it.
- The default GCP location is `us`.
- Windows text injection uses Unicode keyboard events.
- On macOS, local apps default to `Command+V` for clipboard paste fallback.
- On macOS, targets whose app name or bundle ID matches `DICTATION_MACOS_REMOTE_PASTE_TARGETS` default to `Ctrl+Shift+V` for clipboard paste fallback. This is intended for remote terminals shown through RustDesk.
- Windows shows a small live recording meter while audio is being captured.
- Linux text injection uses `xdotool` on X11 or `wtype` on Wayland.
- macOS text injection uses `pbcopy` and `osascript`, and requires Accessibility permission.
- macOS global hotkeys use `pynput`, work while another app has focus, and also require Accessibility permission.
- The default hotkey flow is toggle-to-record: press the hotkey once to start recording, then press it again to transcribe, paste into the focused field, and leave the transcript on the clipboard.
- While recording or transcribing, the app shows a small floating status indicator so you can tell what state it is in even when the main window is hidden.
- The macOS default uses modifiers specifically to avoid common browser `F6` focus shortcuts that jump to the address bar.
- Global hotkeys are currently supported on Windows and macOS. Linux can still use the UI buttons for manual start/stop.
- The GCP backend transcribes one recorded utterance at a time.
- The OpenAI backend uploads one recorded WAV utterance and emits finalized transcripts only.
- The Ollama backend uploads one recorded WAV utterance to the configured `OLLAMA_BASE_URL` and emits finalized transcripts only.

## Project Layout

```text
src/
  speech_to_text_app/
    __init__.py
    __main__.py
    audio.py
    config.py
    hotkeys/
    injectors/
    recognizer.py
    providers/
    ui.py
```
