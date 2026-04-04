# Speech-To-Text Dictation App

This project is a small desktop app written in Python. It records your speech between explicit manual start and stop actions, sends the captured utterance to a speech-to-text provider, and types the finalized transcript into whichever app is currently focused.

## What It Does

- Uses your Windows microphone as the audio source.
- Uses explicit manual start/stop recording instead of silence-based auto-stop.
- Supports Google Cloud Speech-to-Text V2 and OpenAI transcription models.
- Shows finalized transcripts in a local control window.
- Types final transcript text into the active application, such as Windows Terminal, VS Code, Word, or a browser text field.

## Requirements

- Windows
- Python 3.11+ installed and available on `PATH`
- For GCP mode: a Google Cloud project with Speech-to-Text enabled plus local auth
- For OpenAI mode: an `OPENAI_API_KEY`

## Setup

1. Install Python.
2. Create the project virtual environment:

   ```powershell
   python -m virtualenv .venv
   ```

3. Activate the virtual environment before installing or running anything in this project:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies from the activated virtual environment:

   ```powershell
   pip install -e .
   ```

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

   For OpenAI:

   ```powershell
   $env:SPEECH_PROVIDER="openai"
   $env:OPENAI_API_KEY="your-openai-api-key"
   ```

## Run

Set your project ID in the current shell, then start the app:

```powershell
$env:SPEECH_PROVIDER="gcp"
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
.\run.ps1
```

You can also set the location if you want to override the default `us` region:

```powershell
$env:GOOGLE_CLOUD_LOCATION="us"
.\run.ps1
```

If you prefer not to set environment variables, you can pass the project directly:

```powershell
.\run.ps1 -ProjectId your-gcp-project-id
```

OpenAI example:

```powershell
$env:SPEECH_PROVIDER="openai"
$env:OPENAI_API_KEY="your-openai-api-key"
.\run.ps1 -Provider openai
```

Optional location override:

```powershell
.\run.ps1 -Location us
```

Smoke test without opening the UI:

```powershell
.\run.ps1 -SmokeTest
```

## How To Use

1. Launch the app.
2. Confirm the provider, project ID if using GCP, language, and model.
3. Click into the target app where text should appear.
4. Click `Start Recording`.
5. Speak your full prompt, including long pauses if needed.
6. Click `Stop And Transcribe`.

The app only injects finalized transcription results. It does not auto-stop on silence.

## Notes

- The default provider is `gcp`.
- The default GCP model is `chirp_3`.
- The default OpenAI model is `gpt-4o-mini-transcribe`.
- The default GCP location is `us`.
- The app uses Unicode keyboard events, so it can type into most Windows applications without requiring app-specific integrations.
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
    injectors/
    recognizer.py
    providers/
    ui.py
```
