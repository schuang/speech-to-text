# Speech-To-Text Dictation App

This project is a small desktop app written in Python. It records your speech between explicit manual start and stop actions, sends the captured utterance to a speech-to-text provider, and types the finalized transcript into whichever app is currently focused.

## What It Does

- Uses your local microphone as the audio source.
- Uses explicit manual start/stop recording instead of silence-based auto-stop.
- Supports a Windows global hotkey toggle for start/stop recording.
- Supports Google Cloud Speech-to-Text V2 and OpenAI transcription models.
- Shows finalized transcripts in a local control window.
- Types final transcript text into the active application, such as a terminal, VS Code, LibreOffice, Word, or a browser text field.

## Requirements

- Windows, Linux, or macOS
- Python 3.11+ installed and available on `PATH`
- For GCP mode: a Google Cloud project with Speech-to-Text enabled plus local auth
- For OpenAI mode: an `OPENAI_API_KEY`
- For Linux text injection:
  - `xdotool` on X11, or
  - `wtype` on Wayland
- For Linux audio capture with `sounddevice`: PortAudio must be installed at the system level
- For macOS text injection: grant Accessibility access to your terminal app or Python app

## Setup

1. Install Python.
2. Create the project virtual environment:

   ```powershell
   python -m virtualenv .venv
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

5. Choose a provider.

   For Google Cloud:

   ```powershell
   gcloud auth application-default login
   ```

   Or set a service account key path:

   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
   ```

6. Set your provider-specific environment.

   For Google Cloud:

   ```powershell
   $env:SPEECH_PROVIDER="gcp"
   $env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   ```

   Optional: set the Speech-to-Text location. `chirp_3` should use a supported regional location such as `us`.

   ```powershell
   $env:GOOGLE_CLOUD_LOCATION="us"
   ```

   Optional: set the global hotkey. Default is `ctrl+alt+space`. Global hotkeys are currently supported on Windows only.

   ```powershell
   $env:DICTATION_HOTKEY="ctrl+alt+space"
   ```

   For OpenAI:

   ```powershell
   $env:SPEECH_PROVIDER="openai"
   $env:OPENAI_API_KEY="your-openai-api-key"
   ```

## Run

Set your project ID in the current shell, then start the app.

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
2. Confirm the provider, project ID if using GCP, language, and model.
3. Click into the target app where text should appear.
4. Click `Start Recording` or press the global hotkey where supported.
5. Speak your full prompt, including long pauses if needed.
6. Click `Stop And Transcribe` or press the global hotkey again.

The app only injects finalized transcription results. It does not auto-stop on silence.

## Notes

- The default provider is `gcp`.
- The default GCP model is `chirp_3`.
- The default OpenAI model is `gpt-4o-mini-transcribe`.
- The default GCP location is `us`.
- Windows text injection uses Unicode keyboard events.
- Linux text injection uses `xdotool` on X11 or `wtype` on Wayland.
- macOS text injection uses `pbcopy` and `osascript`, and requires Accessibility permission.
- Global hotkeys are currently supported on Windows only. Linux and macOS can still use the UI buttons for manual start/stop.
- The GCP backend transcribes one recorded utterance at a time.
- The OpenAI backend uploads one recorded WAV utterance and emits finalized transcripts only.

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
