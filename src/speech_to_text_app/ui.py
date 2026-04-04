from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk

from .config import AppConfig
from .injector import WindowsTextInjector
from .recognizer import StreamingDictationSession


class DictationApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Speech To Text Dictation")
        self.geometry("760x520")
        self.minsize(680, 460)

        default_config = AppConfig.from_env()
        self.project_id_var = tk.StringVar(value=default_config.project_id)
        self.language_var = tk.StringVar(value=default_config.language_code)
        self.model_var = tk.StringVar(value=default_config.model)
        self.location_var = tk.StringVar(value=default_config.recognizer_location)
        self.status_var = tk.StringVar(value="Idle")
        self.interim_var = tk.StringVar(value="")

        self._events: queue.Queue[tuple[str, str]] = queue.Queue()
        self._session: StreamingDictationSession | None = None

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._pump_events)

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        config_frame = ttk.Frame(self, padding=16)
        config_frame.grid(row=0, column=0, sticky="ew")
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Google Cloud Project ID").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.project_id_var).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Language Code").grid(
            row=1, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.language_var).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Model").grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.model_var).grid(
            row=2, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(config_frame, text="Location").grid(
            row=3, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(config_frame, textvariable=self.location_var).grid(
            row=3, column=1, sticky="ew", pady=(0, 8)
        )

        button_row = ttk.Frame(config_frame)
        button_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.start_button = ttk.Button(
            button_row, text="Start Listening", command=self._start_session
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))

        self.stop_button = ttk.Button(
            button_row, text="Stop", command=self._stop_session, state="disabled"
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
                "Usage: click Start Listening, then click into the target app. "
                "Final transcripts are typed into the active window."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(content, text="Status").grid(row=1, column=0, sticky="w")
        ttk.Label(content, textvariable=self.status_var).grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )

        transcript_frame = ttk.LabelFrame(content, text="Live Transcript Preview")
        transcript_frame.grid(row=3, column=0, sticky="nsew")
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(1, weight=1)

        ttk.Label(transcript_frame, text="Interim").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        ttk.Label(
            transcript_frame,
            textvariable=self.interim_var,
            wraplength=680,
            justify="left",
        ).grid(row=1, column=0, sticky="new", padx=12, pady=(0, 12))

        ttk.Label(transcript_frame, text="Final Text Sent").grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.final_text = tk.Text(transcript_frame, height=10, wrap="word")
        self.final_text.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.final_text.configure(state="disabled")

    def _start_session(self) -> None:
        project_id = self.project_id_var.get().strip()
        if not project_id:
            messagebox.showerror(
                "Missing project ID",
                "Enter a Google Cloud project ID or set GOOGLE_CLOUD_PROJECT.",
            )
            return

        config = AppConfig(
            project_id=project_id,
            language_code=self.language_var.get().strip() or "en-US",
            model=self.model_var.get().strip() or "chirp_3",
            recognizer_location=self.location_var.get().strip() or "us",
        )

        self._session = StreamingDictationSession(
            config=config,
            injector=WindowsTextInjector(),
            on_status=lambda message: self._events.put(("status", message)),
            on_interim=lambda text: self._events.put(("interim", text)),
            on_final=lambda text: self._events.put(("final", text)),
        )
        self._session.start()

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting...")

    def _stop_session(self) -> None:
        if self._session is not None:
            self._session.stop()
            self._session = None

        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_var.set("Stopped.")

    def _pump_events(self) -> None:
        while True:
            try:
                event_type, payload = self._events.get_nowait()
            except queue.Empty:
                break

            if event_type == "status":
                self.status_var.set(payload)
                if payload in {"Stopped.", "Recognition stream ended."} or payload.startswith(
                    "Error:"
                ) or payload.startswith("Google Cloud error:"):
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self._session = None
            elif event_type == "interim":
                self.interim_var.set(payload)
            elif event_type == "final":
                self._append_final_text(payload)

        self.after(100, self._pump_events)

    def _append_final_text(self, text: str) -> None:
        self.final_text.configure(state="normal")
        self.final_text.insert("end", f"{text}\n")
        self.final_text.see("end")
        self.final_text.configure(state="disabled")

    def _on_close(self) -> None:
        self._stop_session()
        self.destroy()


def main() -> None:
    app = DictationApp()
    app.mainloop()
