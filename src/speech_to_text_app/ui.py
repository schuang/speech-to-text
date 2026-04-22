from __future__ import annotations

import os
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .config import AppConfig
from .hotkeys import HotkeyError, HotkeyListener, build_hotkey_listener
from .injectors import TextInjectorError, build_text_injector
from .recognizer import ManualDictationSession
from .recording_meter import RecordingMeter


class DictationApp(tk.Tk):
    _DEFAULT_HOTKEY = "f6" if sys.platform == "darwin" else "ctrl+alt+space"

    def __init__(self) -> None:
        super().__init__()
        self.title("Speech To Text Dictation")
        self.geometry("460x560")
        self.minsize(430, 500)
        self._icon_image: tk.PhotoImage | None = None
        self._set_window_icon()

        default_config = AppConfig.from_env()
        self._provider = default_config.normalized_provider
        self.project_id_var = tk.StringVar(value=default_config.project_id)
        self.language_var = tk.StringVar(value=default_config.language_code)
        self.model_var = tk.StringVar(value=default_config.resolved_model)
        self.hotkey_var = tk.StringVar(value=default_config.hotkey)
        self.location_var = tk.StringVar(value=default_config.recognizer_location)
        self.status_var = tk.StringVar(value="Idle")

        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._session: ManualDictationSession | None = None
        self._hotkey_listener: HotkeyListener | None = None
        self._recording_meter: RecordingMeter | None = None

        self._build_widgets()
        self._start_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._pump_events)

    def _set_window_icon(self) -> None:
        icon_path = Path(__file__).with_name("assets") / "microphone.png"
        if not icon_path.exists():
            return

        try:
            self._icon_image = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self._icon_image)
        except tk.TclError:
            self._icon_image = None

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        config_frame = ttk.Frame(self, padding=16)
        config_frame.grid(row=0, column=0, sticky="ew")
        config_frame.columnconfigure(1, weight=1)
        row = 0

        provider_name = "OpenAI" if self._provider == "openai" else "Google Cloud"
        ttk.Label(config_frame, text="Provider").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(config_frame, text=provider_name).grid(
            row=row, column=1, sticky="w", pady=(0, 8)
        )
        row += 1

        if self._provider == "openai":
            ttk.Label(config_frame, text="API Key").grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            ttk.Label(config_frame, text="Loaded from OPENAI_API_KEY").grid(
                row=row, column=1, sticky="w", pady=(0, 8)
            )
            row += 1
        else:
            ttk.Label(config_frame, text="Google Cloud Project ID").grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            ttk.Entry(config_frame, textvariable=self.project_id_var).grid(
                row=row, column=1, sticky="ew", pady=(0, 8)
            )
            row += 1

            ttk.Label(config_frame, text="Location").grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            ttk.Entry(config_frame, textvariable=self.location_var).grid(
                row=row, column=1, sticky="ew", pady=(0, 8)
            )
            row += 1

        ttk.Label(config_frame, text="Language Code").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.language_var).grid(
            row=row, column=1, sticky="ew", pady=(0, 8)
        )
        row += 1

        ttk.Label(config_frame, text="Model").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.model_var).grid(
            row=row, column=1, sticky="ew", pady=(0, 8)
        )
        row += 1

        ttk.Label(config_frame, text="Global Hotkey").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.hotkey_var).grid(
            row=row, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Button(
            config_frame,
            text="Apply",
            command=self._restart_hotkey_listener,
        ).grid(row=row, column=2, sticky="w", padx=(8, 0), pady=(0, 8))
        row += 1

        button_row = ttk.Frame(config_frame)
        button_row.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.start_button = ttk.Button(
            button_row, text="Start Recording", command=self._start_session
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))

        self.stop_button = ttk.Button(
            button_row,
            text="Stop And Transcribe",
            command=self._stop_session,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 8))

        ttk.Button(button_row, text="Hide Window", command=self.iconify).grid(
            row=0, column=2
        )

        if sys.platform == "win32":
            self._recording_meter = RecordingMeter(button_row)
            self._recording_meter.grid(row=0, column=3, padx=(12, 0), sticky="w")

        content = ttk.Frame(self, padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        ttk.Label(
            content,
            text=(
                "Usage: click Start Recording, speak your full prompt or paragraph, "
                "then click Stop And Transcribe. On macOS, the default hotkey is F6: "
                "press and hold F6 to record, then release to transcribe, paste into "
                "the focused app, and "
                "copy the transcript to the clipboard. The manual buttons remain as a "
                "fallback."
            ),
            wraplength=400,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(content, text="Status").grid(row=1, column=0, sticky="w")
        ttk.Label(content, textvariable=self.status_var).grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )

        transcript_frame = ttk.LabelFrame(content, text="Captured Transcript")
        transcript_frame.grid(row=3, column=0, sticky="nsew")
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)

        ttk.Label(transcript_frame, text="Final Text Sent").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.final_text = tk.Text(transcript_frame, height=10, wrap="word")
        self.final_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.final_text.configure(state="disabled")

    def _start_session(self) -> None:
        if self._session is not None and (self._session.recording or self._session.transcribing):
            return

        provider = self._provider
        project_id = self.project_id_var.get().strip()
        if provider == "gcp" and not project_id:
            messagebox.showerror(
                "Missing project ID",
                "Enter a Google Cloud project ID or set GOOGLE_CLOUD_PROJECT for GCP mode.",
            )
            return
        if provider == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
            messagebox.showerror(
                "Missing OpenAI API key",
                "Set OPENAI_API_KEY before starting OpenAI mode.",
            )
            return

        config = AppConfig(
            provider=provider,
            project_id=project_id,
            language_code=self.language_var.get().strip() or "en-US",
            model=self.model_var.get().strip()
            or ("gpt-4o-mini-transcribe" if provider == "openai" else "chirp_3"),
            hotkey=self.hotkey_var.get().strip() or self._DEFAULT_HOTKEY,
            recognizer_location=self.location_var.get().strip() or "us",
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        )

        try:
            injector = build_text_injector(delay_seconds=config.typing_delay_seconds)
        except TextInjectorError as error:
            messagebox.showerror("Injector unavailable", str(error))
            return

        self._session = ManualDictationSession(
            config=config,
            injector=injector,
            on_status=lambda message: self._events.put(("status", message)),
            on_final=lambda text: self._events.put(("final", text)),
            on_level=lambda level: self._events.put(("level", level)),
        )
        self._session.start_recording()

        if self._session.recording:
            self._show_recording_meter()

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting recording...")

    def _stop_session(self) -> None:
        if self._session is not None:
            self._session.stop_recording()

        self._hide_recording_meter()
        self.stop_button.configure(state="disabled")
        self.status_var.set("Stopping recording...")

    def _pump_events(self) -> None:
        while True:
            try:
                event_type, payload = self._events.get_nowait()
            except queue.Empty:
                break

            if event_type == "status":
                self.status_var.set(payload)
                if payload in {
                    "No audio captured.",
                    "No speech detected.",
                    "Transcript pasted into the focused app and copied to the clipboard.",
                } or payload.startswith("Error:") or payload.startswith(
                    "Speech provider error:"
                ) or payload.startswith("Typing failed:"):
                    self._hide_recording_meter()
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    if self._session is not None and not self._session.recording:
                        self._session = None
            elif event_type == "hotkey_press":
                self._handle_hotkey_press()
            elif event_type == "hotkey_release":
                self._handle_hotkey_release()
            elif event_type == "toggle":
                self._toggle_recording()
            elif event_type == "final":
                self._append_final_text(payload)
            elif event_type == "level":
                self._update_recording_meter(float(payload))

        self.after(100, self._pump_events)

    def _append_final_text(self, text: str) -> None:
        self.final_text.configure(state="normal")
        self.final_text.insert("end", f"{text}\n")
        self.final_text.see("end")
        self.final_text.configure(state="disabled")

    def _handle_hotkey_press(self) -> None:
        if self._session is not None and self._session.transcribing:
            self.status_var.set("Transcription still in progress.")
            return

        self._start_session()

    def _handle_hotkey_release(self) -> None:
        if self._session is not None and self._session.recording:
            self._stop_session()

    def _toggle_recording(self) -> None:
        if self._session is not None and self._session.recording:
            self._stop_session()
            return

        if self._session is not None and self._session.transcribing:
            self.status_var.set("Transcription still in progress.")
            return

        self._start_session()

    def _restart_hotkey_listener(self) -> None:
        self._start_hotkey_listener()

    def _start_hotkey_listener(self) -> None:
        hotkey = self.hotkey_var.get().strip() or self._DEFAULT_HOTKEY

        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None

        try:
            if sys.platform == "darwin":
                callback = lambda: self._events.put(("hotkey_press", ""))
                release_callback = lambda: self._events.put(("hotkey_release", ""))
            else:
                callback = lambda: self._events.put(("toggle", ""))
                release_callback = None

            self._hotkey_listener = build_hotkey_listener(
                hotkey=hotkey,
                callback=callback,
                release_callback=release_callback,
            )
            self._hotkey_listener.start()
            if sys.platform == "darwin":
                self.status_var.set(f"Idle. Hold hotkey to talk: {hotkey}")
            else:
                self.status_var.set(f"Idle. Toggle hotkey ready: {hotkey}")
        except HotkeyError as error:
            self._hotkey_listener = None
            self.status_var.set(f"Hotkey unavailable: {error}")

    def _show_recording_meter(self) -> None:
        if self._recording_meter is None:
            return
        self._recording_meter.show()

    def _hide_recording_meter(self) -> None:
        if self._recording_meter is None:
            return
        self._recording_meter.hide()

    def _update_recording_meter(self, level: float) -> None:
        if self._recording_meter is None:
            return
        self._recording_meter.update_level(level)

    def _on_close(self) -> None:
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._recording_meter is not None:
            self._recording_meter.close()
            self._recording_meter = None
        self.destroy()


def main() -> None:
    app = DictationApp()
    app.mainloop()
