# Windows Speech-To-Text Dictation App

This project is a small Windows desktop app written in Python. It listens to your microphone, streams audio to Google Cloud Speech-to-Text, and types finalized transcripts into whichever Windows app is currently focused.

## What It Does

- Uses your Windows microphone as the audio source.
- Streams audio to Google Cloud Speech-to-Text V2.
- Shows interim and final transcripts in a local control window.
- Types final transcript text into the active application, such as Windows Terminal, VS Code, Word, or a browser text field.

## Requirements

- Windows
- Python 3.11+ installed and available on `PATH`
- A Google Cloud project with Speech-to-Text enabled
- Application Default Credentials or a service account key

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

5. Authenticate with Google Cloud. Either:

   ```powershell
   gcloud auth application-default login
   ```

   Or set a service account key path:

   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
   ```

6. Set your project ID:

   ```powershell
   $env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   ```

7. Optional: set the Speech-to-Text location. `chirp_3` should use a supported regional location such as `us`.

   ```powershell
   $env:GOOGLE_CLOUD_LOCATION="us"
   ```

## Run

Set your project ID in the current shell, then start the app:

```powershell
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
2. Confirm the project ID, language, and model.
3. Click `Start Listening`.
4. Click into the target app where text should appear.
5. Speak into your microphone.
6. Click `Stop` in the app to end dictation.

The app only injects finalized recognition results. Interim text is displayed in the UI but not typed into the target application.

## Notes

- The default model is `chirp_3`.
- The default location is `us`.
- The app uses Unicode keyboard events, so it can type into most Windows applications without requiring app-specific integrations.
- Google Cloud streaming requests have tight per-message audio size limits. This app sends short PCM chunks to stay within those limits.

## Project Layout

```text
src/
  speech_to_text_app/
    __init__.py
    __main__.py
    audio.py
    config.py
    injector.py
    recognizer.py
    ui.py
```
