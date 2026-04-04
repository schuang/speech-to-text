from __future__ import annotations

import os
import queue
import tkinter as tk
from tkinter import messagebox, ttk

from .config import AppConfig
from .hotkeys import WindowsHotkeyError, WindowsHotkeyListener
from .injectors import WindowsTextInjector
from .recognizer import ManualDictationSession


class DictationApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Speech To Text Dictation")
        self.geometry("760x520")
        self.minsize(680, 460)

        default_config = AppConfig.from_env()
        self.provider_var = tk.StringVar(value=default_config.provider)
        self.project_id_var = tk.StringVar(value=default_config.project_id)
        self.language_var = tk.StringVar(value=default_config.language_code)
        self.model_var = tk.StringVar(value=default_config.resolved_model)
        self.hotkey_var = tk.StringVar(value=default_config.hotkey)
        self.location_var = tk.StringVar(value=default_config.recognizer_location)
        self.status_var = tk.StringVar(value="Idle")

        self._events: queue.Queue[tuple[str, str]] = queue.Queue()
        self._session: ManualDictationSession | None = None
        self._hotkey_listener: WindowsHotkeyListener | None = None

        self._build_widgets()
        self._start_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._pump_events)

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        config_frame = ttk.Frame(self, padding=16)
        config_frame.grid(row=0, column=0, sticky="ew")
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Provider").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.provider_var).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Google Cloud Project ID (GCP only)").grid(
            row=1, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.project_id_var).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Language Code").grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.language_var).grid(
            row=2, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Model").grid(
            row=3, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.model_var).grid(
            row=3, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Location (GCP only)").grid(
            row=4, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.location_var).grid(
            row=4, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Global Hotkey").grid(
            row=5, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.hotkey_var).grid(
            row=5, column=1, sticky="ew", pady=(0, 8)
        )

        button_row = ttk.Frame(config_frame)
        button_row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

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

        content = ttk.Frame(self, padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        ttk.Label(
            content,
            text=(
                "Usage: click Start Recording, speak your full prompt or paragraph, "
                "then click Stop And Transcribe. The global hotkey also toggles start "
                "and stop. Final transcript text is typed into the active window."
            ),
            wraplength=700,
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

        provider = self.provider_var.get().strip().lower() or "gcp"
        if provider not in {"gcp", "openai"}:
            messagebox.showerror(
                "Unsupported provider",
                "Provider must be either 'gcp' or 'openai'.",
            )
            return

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
            hotkey=self.hotkey_var.get().strip() or "ctrl+alt+space",
            recognizer_location=self.location_var.get().strip() or "us",
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        )

        self._session = ManualDictationSession(
            config=config,
            injector=WindowsTextInjector(),
            on_status=lambda message: self._events.put(("status", message)),
            on_final=lambda text: self._events.put(("final", text)),
        )
        self._session.start_recording()

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting recording...")

    def _stop_session(self) -> None:
        if self._session is not None:
            self._session.stop_recording()

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
                    "Transcription inserted.",
                } or payload.startswith("Error:") or payload.startswith(
                    "Speech provider error:"
                ) or payload.startswith("Typing failed:"):
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    if self._session is not None and not self._session.recording:
                        self._session = None
            elif event_type == "toggle":
                self._toggle_recording()
            elif event_type == "final":
                self._append_final_text(payload)

        self.after(100, self._pump_events)

    def _append_final_text(self, text: str) -> None:
        self.final_text.configure(state="normal")
        self.final_text.insert("end", f"{text}\n")
        self.final_text.see("end")
        self.final_text.configure(state="disabled")

    def _toggle_recording(self) -> None:
        if self._session is not None and self._session.recording:
            self._stop_session()
            return

        if self._session is not None and self._session.transcribing:
            self.status_var.set("Transcription still in progress.")
            return

        self._start_session()

    def _start_hotkey_listener(self) -> None:
        hotkey = self.hotkey_var.get().strip() or "ctrl+alt+space"
        try:
            self._hotkey_listener = WindowsHotkeyListener(
                hotkey=hotkey,
                callback=lambda: self._events.put(("toggle", "")),
            )
            self._hotkey_listener.start()
            self.status_var.set(f"Idle. Hotkey ready: {hotkey}")
        except WindowsHotkeyError as error:
            self._hotkey_listener = None
            self.status_var.set(f"Hotkey unavailable: {error}")

    def _on_close(self) -> None:
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._session is not None:
            self._session.close()
            self._session = None
        self.destroy()


def main() -> None:
    app = DictationApp()
    app.mainloop()
