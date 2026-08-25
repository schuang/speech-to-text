# Speech-To-Text Dictation App

This project is a small desktop app written in Python. It records your speech between explicit manual start and stop actions, sends the captured utterance to a speech-to-text provider, pastes the finalized transcript into whichever app is currently focused, and leaves the transcript on the clipboard.

## What It Does

- Uses your local microphone as the audio source.
- Shows a microphone selector when multiple USB input devices are connected.
- Uses explicit manual start/stop recording instead of silence-based auto-stop.
- Supports global hotkeys on macOS and Windows.
- Shows a small Windows recording meter while audio is being captured.
- Supports Google Cloud Speech-to-Text V2, OpenAI, and local Faster Whisper transcription models.
- Converts existing audio files such as `.m4a`, `.mp3`, and `.wav` to UTF-8 text with the local Faster Whisper model.
- Optionally labels speaker turns with a second local diarization model.
- Detects the active provider from your environment.
- Shows finalized transcripts in a local control window.
- Pastes final transcript text into the active application, such as a terminal, VS Code, LibreOffice, Word, or a browser text field.
- Copies the finalized transcript to the clipboard.

## Requirements

- Windows, Linux, or macOS
- `uv`, or Python 3.11+ installed and available on `PATH`
- For the default GCP mode: a Google Cloud project with Speech-to-Text enabled plus local auth
- For OpenAI mode: an `OPENAI_API_KEY`
- For local mode: enough disk space to download the selected Faster Whisper model on first use
- For Linux text injection:
  - `xdotool` on X11, or
  - `wtype` on Wayland
- For Linux clipboard support: `xclip` or `xsel` on X11, or `wl-copy` on Wayland
- For Linux audio capture with `sounddevice`: PortAudio must be installed at the system level
- For macOS text injection: grant Accessibility access to your terminal app or Python app
- For macOS global hotkeys: Accessibility access is also required
- For macOS remote terminals in RustDesk: the app now uses `Ctrl+Shift+V` by default when the focused target is RustDesk. Override with `DICTATION_MACOS_REMOTE_PASTE_SHORTCUT` if your remote terminal expects a different paste chord.

## Setup

### Using uv

Install `uv` if needed:

```cmd
winget install --id=astral-sh.uv -e
```

Close and reopen your terminal, then sync the project dependencies from the project directory:

```cmd
cd %USERPROFILE%\Documents\speech-to-text
uv sync
```

`uv sync` creates the project `.venv` and installs the package dependencies from `pyproject.toml`. If a compatible Python is not already installed, `uv` can download one automatically. To install a specific Python version first:

```cmd
uv python install 3.13
uv sync
```

### Using venv and pip

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

5. Configure the provider you want to use. The launcher scripts default to local Faster Whisper:

   ```powershell
   gcloud auth application-default login
   ```

   Or set a service account key path:

   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
   ```

6. Set your provider-specific environment.

   Launcher provider selection works like this:

   - `run.sh`, `run.ps1`, and `run.cmd` use local Faster Whisper by default.
   - Use `--provider` with `run.sh` or `-Provider` with the Windows launchers to select GCP or OpenAI.
   - Direct `python -m speech_to_text_app` launches still read `SPEECH_PROVIDER` and default to GCP when it is unset.

   For Google Cloud Speech-to-Text:

   ```powershell
   $env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
   ```

   Optional: set the Speech-to-Text location. `chirp_3` should use a supported regional location such as `us`.

   ```powershell
   $env:GOOGLE_CLOUD_LOCATION="us"
   ```

   Optional: set the primary global hotkey. On macOS the defaults are `ctrl+shift+space` and the secondary `F19` key. On Windows the default is `ctrl+alt+space`. Global hotkeys are currently supported on Windows and macOS.

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
   $env:OPENAI_API_KEY="your-openai-api-key"
   ```

   For local transcription, follow [Local Faster Whisper Setup](#local-faster-whisper-setup). Local mode does not require a cloud account or API key.

## Local Faster Whisper Setup

Faster Whisper runs transcription on the computer. Audio is not uploaded to Google Cloud or OpenAI when `SPEECH_PROVIDER=local`. Installing the Python dependencies and downloading a model require internet access once; after that, local transcription can run offline.

The portable defaults are:

```text
Provider:     local
Model:        base.en
Device:       cpu
Compute type: int8
```

### Windows: fresh installation

Install Python 3.11 or newer, then clone and launch the project:

```powershell
git clone https://github.com/schuang/speech-to-text.git
cd speech-to-text
.\run.ps1 -Provider local
```

The PowerShell launcher creates `.venv` when needed and installs the dependencies declared by the project. If PowerShell script execution is blocked, use the Command Prompt launcher:

```bat
run.cmd -Provider local
```

You can also configure the local model through environment variables:

```powershell
$env:SPEECH_MODEL="base.en"
$env:LOCAL_WHISPER_DEVICE="cpu"
$env:LOCAL_WHISPER_COMPUTE_TYPE="int8"
.\run.ps1
```

### Linux: fresh installation

On Ubuntu or Debian, install Python, Tkinter, PortAudio, and the desktop integration tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk libportaudio2 xdotool wtype xclip wl-clipboard
```

Clone the project and install it into a virtual environment:

```bash
git clone https://github.com/schuang/speech-to-text.git
cd speech-to-text
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

export SPEECH_MODEL="base.en"
export LOCAL_WHISPER_DEVICE="cpu"
export LOCAL_WHISPER_COMPUTE_TYPE="int8"
./run.sh
```

Linux global hotkeys are not currently enabled, so use the graphical Start Recording and Stop And Transcribe buttons.

### macOS: fresh installation

Install Python 3.11 or newer with Tkinter support and ensure PortAudio is available. Then run:

```bash
git clone https://github.com/schuang/speech-to-text.git
cd speech-to-text
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

export SPEECH_MODEL="base.en"
export LOCAL_WHISPER_DEVICE="cpu"
export LOCAL_WHISPER_COMPUTE_TYPE="int8"
./run.sh
```

Grant Microphone access so the app can record. Grant Accessibility access to the terminal or Python application so global hotkeys and text insertion work. Faster Whisper uses CPU inference on macOS; the NVIDIA CUDA path is for supported Windows and Linux systems.

### Download the model before first use

Normally, the selected model downloads automatically when the first recording is transcribed. To download and validate `base.en` in advance, activate the project virtual environment and run:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8'); print('Model ready')"
```

On Windows, the same command can be run without activating the environment:

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8'); print('Model ready')"
```

The model is cached rather than stored in this Git repository. Default cache locations are:

- Windows: `C:\Users\<username>\.cache\huggingface\hub`
- Linux and macOS: `~/.cache/huggingface/hub`

Set `HF_HOME` before downloading if the cache should live somewhere else. For a computer that must remain offline, install the Python dependencies and pre-download the model while connected, or copy the complete Hugging Face model cache from another compatible installation.

### Choose a local model

| Model | Language | Tradeoff |
|---|---|---|
| `tiny.en` | English only | Fastest, with the lowest accuracy |
| `base.en` | English only | Default; recommended starting point |
| `base` | Multilingual | Use for Mandarin and other non-English speech |
| `small.en` | English only | Better accuracy, but slower and larger |
| `small` | Multilingual | Better multilingual accuracy, but slower and larger |

When a non-English language is selected, the UI automatically changes an English-only model to its multilingual counterpart—for example, `base.en` becomes `base` and `small.en` becomes `small`. If the language is changed back to English, the UI restores the English-only model it changed automatically. A multilingual model selected manually is left unchanged. The first transcription after each application launch includes model-loading time; later recordings reuse the model already held in memory.

### Mandarin example

Mandarin requires a multilingual model. Do not use `base.en` or another model ending in `.en`.

On Windows PowerShell, start local mode with the multilingual `base` model:

```powershell
$env:SPEECH_MODEL="base"
$env:LOCAL_WHISPER_DEVICE="cpu"
$env:LOCAL_WHISPER_COMPUTE_TYPE="int8"
.\run.ps1
```

On Linux or macOS:

```bash
export SPEECH_MODEL="base"
export LOCAL_WHISPER_DEVICE="cpu"
export LOCAL_WHISPER_COMPUTE_TYPE="int8"
./run.sh
```

In the graphical UI, set **Language** to **Chinese (Mandarin, Taiwan)** before recording. For example, dictate:

```text
請幫我安排明天下午三點的會議，並提醒我準備專案進度報告。
```

This means: “Please schedule a meeting for three o'clock tomorrow afternoon, and remind me to prepare the project status report.” The model downloads on the first Mandarin transcription if it is not already cached; later use is local and offline.

CPU INT8 is the cross-platform configuration. Advanced Windows or Linux installations with a compatible NVIDIA GPU can set `LOCAL_WHISPER_DEVICE=cuda` and a supported compute type such as `int8_float16`, but CUDA and cuDNN must be installed separately. If those libraries are not configured, keep the CPU defaults.

## Transcribe an Audio File on macOS

File transcription always uses the local Faster Whisper provider, even if the current shell is configured for a cloud provider. Faster Whisper's media decoder supports common formats including M4A, MP3, WAV, AAC, FLAC, Ogg, and Opus.

In the desktop app's **Audio File Transcription** section, click **Choose…** beside **Audio File**. The selected audio path and default output `.txt` path are displayed in editable fields. Review or edit either path, optionally choose a different output file or enable **Identify speakers**, then click **Start Transcribing**. Selecting a file does not start transcription.

The same operation is available from Terminal:

```bash
./run.sh test.m4a
./run.sh meeting.m4a --output meeting.txt
```

The output defaults to the audio filename with a `.txt` extension. Existing text files are preserved unless `--force` is supplied:

```bash
./run.sh meeting.m4a --output meeting.txt --force
```

Choose a different local Whisper model or spoken language when needed:

```bash
./run.sh interview.m4a --model small.en --language en-US
./run.sh interview-zh.m4a --model small --language zh
```

### Local speaker labels

Speaker diarization answers “who spoke when” and labels turns as `Speaker 1`, `Speaker 2`, and so on. It does not infer people's names. The pyannote dependency is included in the project requirements. Ensure the environment is current and install the macOS media decoder:

The output places a blank line between timestamped speaker turns for readability.

```bash
brew install ffmpeg
source .venv/bin/activate
pip install -e .
```

Then accept the access terms for the [pyannote Community-1 model](https://huggingface.co/pyannote/speaker-diarization-community-1), create a Hugging Face access token, and run:

```bash
export HF_TOKEN="your-hugging-face-token"
./run.sh interview.m4a --speaker-labels
```

If the speaker count is known, supplying it can improve the result:

```bash
./run.sh interview.m4a --num-speakers 2
```

When `--num-speakers` is omitted, pyannote estimates the number of speakers automatically. Use `--speaker-labels` to enable that automatic mode:

```bash
./run.sh interview.m4a --speaker-labels
```

Whisper and pyannote both run on the Mac. They download their model files on first use and can use the cached files offline afterward. Speaker labeling is substantially slower and uses more memory than transcription alone. To use a pyannote model already stored on disk, set `LOCAL_DIARIZATION_MODEL` to that directory.

On macOS, the app decodes audio through Faster Whisper's bundled PyAV decoder and passes a 16 kHz in-memory waveform to pyannote. This avoids dependency on TorchCodec's dynamic FFmpeg library lookup; the Homebrew `ffmpeg` executable remains useful for general media inspection and conversion.

Speaker diarization automatically uses Apple's MPS accelerator when PyTorch can access it and displays progress for segmentation, embeddings, and clustering. To force the CPU path or tune accelerator batch sizes:

```bash
export LOCAL_DIARIZATION_DEVICE=cpu
export LOCAL_DIARIZATION_SEGMENTATION_BATCH_SIZE=1
export LOCAL_DIARIZATION_EMBEDDING_BATCH_SIZE=1
```

The default batch size is 16 on MPS or CUDA and 1 on CPU. A 56-minute recording can still take a while, especially on CPU; the progress display includes an estimated time remaining.

Terminal file conversion displays a progress bar for Faster Whisper transcription as well, followed by separate pyannote progress bars when speaker labels are enabled.

## Run

Set your provider environment in the current shell, then start the app.

Windows Command Prompt with `uv`:

```cmd
cd %USERPROFILE%\Documents\speech-to-text
set GOOGLE_CLOUD_PROJECT=your-gcp-project-id
uv run python -m speech_to_text_app
```

OpenAI from Windows Command Prompt with `uv`:

```cmd
cd %USERPROFILE%\Documents\speech-to-text
set SPEECH_PROVIDER=openai
set OPENAI_API_KEY=your-openai-api-key
uv run python -m speech_to_text_app
```

Windows:

```powershell
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
.\run.ps1 -Provider gcp
```

Windows Command Prompt:

```bat
set GOOGLE_CLOUD_PROJECT=your-gcp-project-id
run.cmd -Provider gcp
```

Linux:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run.sh --provider gcp
```

macOS:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run.sh --provider gcp
```

You can also set the location if you want to override the default `us` region:

```powershell
$env:GOOGLE_CLOUD_LOCATION="us"
.\run.ps1 -Provider gcp
```

If you prefer not to set environment variables, you can pass the project directly on Windows:

```powershell
.\run.ps1 -Provider gcp -ProjectId your-gcp-project-id
```

Show the detailed recording workflow without opening the graphical UI:

```powershell
.\run.ps1 --help
```

On Linux or macOS, use `./run.sh --help`.

OpenAI example:

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
.\run.ps1 -Provider openai
```

OpenAI from Windows Command Prompt:

```bat
set OPENAI_API_KEY=your-openai-api-key
run.cmd -Provider openai
```

Linux OpenAI example:

```bash
export OPENAI_API_KEY="your-openai-api-key"
./run.sh --provider openai
```

macOS OpenAI example:

```bash
export OPENAI_API_KEY="your-openai-api-key"
./run.sh --provider openai
```

OpenAI on Linux or macOS:

```bash
export OPENAI_API_KEY="your-openai-api-key"
./run.sh --provider openai
```

Optional location override:

```powershell
.\run.ps1 -Provider gcp -Location us
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
5. Click into the target app where text should appear.
6. Click `Start Recording` or use the global hotkey where supported.
7. Speak your full prompt, including long pauses if needed.
8. Click `Stop And Transcribe`, or press the hotkey again to stop recording, transcribe, and paste into the currently focused app.

The app only injects finalized transcription results. It does not auto-stop on silence. Finalized text is also copied to the clipboard.

To transcribe an existing recording instead, choose the audio file in **Audio File Transcription**, review or change the displayed output path, optionally enable **Identify speakers**, and click **Start Transcribing**.

## Notes

- The launcher scripts default to the local provider; use their provider option to select GCP or OpenAI.
- Direct module launches read `SPEECH_PROVIDER` when set and otherwise use Google Cloud Speech-to-Text.
- The UI no longer exposes provider editing. It shows only the fields relevant to the detected provider.
- When OpenAI is active, the UI hides Google Cloud project and location fields.
- When Google Cloud is active, the UI hides OpenAI-specific status rows.
- The default GCP model is `chirp_3`.
- The default OpenAI model is `gpt-4o-mini-transcribe`.
- The default local model is `base.en`, using CPU INT8 inference.
- Local Faster Whisper downloads its model on first use, then transcribes offline from the cached model.
- Set `SPEECH_MODEL=base` when using the local provider for Mandarin or other non-English speech.
- Set `LOCAL_WHISPER_DEVICE` and `LOCAL_WHISPER_COMPUTE_TYPE` to opt into a supported accelerator configuration.
- The default GCP location is `us`.
- The GUI language field is a dropdown with presets for English (United States) and Chinese (Mandarin, Taiwan). You can still type a locale manually if you need a different language code.
- When two or more USB microphones are detected at startup, the selected microphone is used for subsequent recordings. With fewer USB microphones, the system default input remains active.
- Windows text injection uses Unicode keyboard events.
- On macOS, local apps default to `Command+V` for clipboard paste fallback.
- On macOS, browser targets use clipboard paste so web text inputs receive the normal paste event.
- On macOS, targets whose app name or bundle ID matches `DICTATION_MACOS_REMOTE_PASTE_TARGETS` default to `Ctrl+Shift+V` for clipboard paste fallback. This is intended for remote terminals shown through RustDesk.
- Windows shows a small live recording meter while audio is being captured.
- Linux text injection uses `xdotool` on X11 or `wtype` on Wayland.
- macOS text injection uses `pbcopy` and `osascript`, and requires Accessibility permission.
- macOS global hotkeys use `pynput`, work while another app has focus, and also require Accessibility permission.
- macOS registers `F19` as a secondary hotkey in addition to the configurable primary hotkey.
- The default hotkey flow is toggle-to-record: press the hotkey once to start recording, then press it again to transcribe, paste into the focused field, and leave the transcript on the clipboard.
- While recording or transcribing, the app shows a small floating status indicator so you can tell what state it is in even when the main window is hidden.
- The macOS default uses modifiers specifically to avoid common browser `F6` focus shortcuts that jump to the address bar.
- Global hotkeys are currently supported on Windows and macOS. Linux can still use the UI buttons for manual start/stop.
- The GCP backend transcribes one recorded utterance at a time.
- The OpenAI backend uploads one recorded WAV utterance and emits finalized transcripts only.
- The Faster Whisper backend processes recorded utterances locally and caches loaded models for reuse between recordings.
- Audio-file conversion always uses Faster Whisper locally and never uploads the selected file.
- Speaker labels use the local pyannote Community-1 model when requested; the labels are anonymous and may be imperfect for overlapping speech or noisy recordings.

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
