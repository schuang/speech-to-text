from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import (
    AppConfig,
    LANGUAGE_OPTIONS,
    compatible_local_model,
    language_code_for_selection,
)
from .hotkeys import HotkeyError, HotkeyListener, build_hotkey_listener
from .injectors import TextInjectorError, build_text_injector
from .microphones import InputDevice, input_device_name, usb_input_devices
from .providers import provider_profile
from .recognizer import ManualDictationSession
from .recording_indicator import FloatingRecordingIndicator
from .recording_meter import RecordingMeter


class DictationApp(tk.Tk):
    _DEFAULT_HOTKEY = "ctrl+shift+space" if sys.platform == "darwin" else "ctrl+alt+space"
    _MACOS_SECONDARY_HOTKEY = "f19"

    def __init__(self) -> None:
        super().__init__()
        self.title("Speech To Text Dictation")
        self.geometry("500x640")
        self.minsize(430, 420)
        self._icon_image: tk.PhotoImage | None = None
        self._set_window_icon()

        default_config = AppConfig.from_env()
        self._provider = default_config.normalized_provider
        self._provider_profile = provider_profile(self._provider)
        self._provider_fields = self._provider_profile.fields(default_config)
        self._provider_field_vars: dict[str, tk.StringVar] = {
            field.key: tk.StringVar(value=field.value)
            for field in self._provider_fields
        }
        self.language_var = tk.StringVar(value=default_config.language_display_name)
        self.model_var = tk.StringVar(
            value=default_config.model or self._provider_profile.default_model
        )
        self.hotkey_var = tk.StringVar(value=default_config.hotkey)
        self.speaker_labels_var = tk.BooleanVar(value=False)
        self._usb_microphones: tuple[InputDevice, ...] = usb_input_devices()
        self.microphone_var = tk.StringVar(value=input_device_name())
        self.status_var = tk.StringVar(value="Idle")

        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._session: ManualDictationSession | None = None
        self._hotkey_listeners: list[HotkeyListener] = []
        self._automatic_local_model_pair: tuple[str, str] | None = None
        self._recording_indicator = FloatingRecordingIndicator(self)
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

        ttk.Label(config_frame, text="Provider").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(config_frame, text=self._provider_profile.display_name).grid(
            row=row, column=1, sticky="w", pady=(0, 8)
        )
        row += 1

        ttk.Label(config_frame, text="Microphone").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        if len(self._usb_microphones) > 1:
            ttk.Combobox(
                config_frame,
                textvariable=self.microphone_var,
                values=[
                    self.microphone_var.get(),
                    *(device.label for device in self._usb_microphones),
                ],
                state="readonly",
            ).grid(row=row, column=1, columnspan=2, sticky="ew", pady=(0, 8))
        else:
            ttk.Label(
                config_frame,
                textvariable=self.microphone_var,
                wraplength=300,
            ).grid(row=row, column=1, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        for field in self._provider_fields:
            ttk.Label(config_frame, text=field.label).grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            if field.editable:
                ttk.Entry(
                    config_frame,
                    textvariable=self._provider_field_vars[field.key],
                ).grid(row=row, column=1, sticky="ew", pady=(0, 8))
            else:
                ttk.Label(config_frame, text=f"Loaded from {field.source}").grid(
                    row=row, column=1, sticky="w", pady=(0, 8)
                )
            row += 1

        ttk.Label(config_frame, text="Language").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        language_combo = ttk.Combobox(
            config_frame,
            textvariable=self.language_var,
            values=[option.label for option in LANGUAGE_OPTIONS],
        )
        language_combo.grid(
            row=row, column=1, sticky="ew", pady=(0, 8)
        )
        language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)
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

        if sys.platform == "darwin":
            ttk.Label(config_frame, text="Secondary Hotkey").grid(
                row=row, column=0, sticky="w", pady=(0, 8)
            )
            ttk.Label(
                config_frame,
                text=self._MACOS_SECONDARY_HOTKEY.upper(),
            ).grid(row=row, column=1, sticky="w", pady=(0, 8))
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

        row += 1
        file_row = ttk.Frame(config_frame)
        file_row.grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.file_button = ttk.Button(
            file_row,
            text="Transcribe Audio File…",
            command=self._choose_audio_file,
        )
        self.file_button.grid(row=0, column=0, padx=(0, 12))
        if self._provider == "local":
            ttk.Checkbutton(
                file_row,
                text="Identify speakers",
                variable=self.speaker_labels_var,
            ).grid(row=0, column=1, sticky="w")

        content = ttk.Frame(self, padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        transcript_frame = ttk.LabelFrame(content, text="Captured Transcript")
        transcript_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(1, weight=1)

        ttk.Label(transcript_frame, text="Final Text Sent").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.final_text = tk.Text(transcript_frame, height=10, wrap="word")
        self.final_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.final_text.configure(state="disabled")

        ttk.Label(content, text="Status").grid(row=1, column=0, sticky="w")
        ttk.Label(content, textvariable=self.status_var).grid(
            row=2, column=0, sticky="w"
        )

    def _start_session(self) -> None:
        if self._session is not None and (self._session.recording or self._session.transcribing):
            return

        config = self._current_config()
        if config is None:
            return

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
        if len(self._usb_microphones) <= 1:
            self.microphone_var.set(self._session.microphone_name)

        if self._session.recording:
            self._clear_final_text()
            self._show_recording_meter()
            self.after(75, self._restore_recording_target)

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting recording...")

    def _current_config(self) -> AppConfig | None:
        provider_values = {
            key: value.get().strip()
            for key, value in self._provider_field_vars.items()
        }
        validation_error = self._provider_profile.validate(provider_values)
        if validation_error:
            messagebox.showerror("Provider unavailable", validation_error)
            return

        language_code = language_code_for_selection(self.language_var.get())
        selected_model = self.model_var.get().strip() or self._provider_profile.default_model
        if self._provider == "local":
            compatible_model = compatible_local_model(selected_model, language_code)
            if compatible_model != selected_model:
                self._automatic_local_model_pair = (
                    selected_model,
                    compatible_model,
                )
                selected_model = compatible_model
                self.model_var.set(selected_model)

        return AppConfig(
            provider=self._provider,
            project_id=provider_values.get("project_id", ""),
            language_code=language_code,
            model=selected_model,
            hotkey=self.hotkey_var.get().strip() or self._DEFAULT_HOTKEY,
            recognizer_location=provider_values.get("recognizer_location", "us") or "us",
            openai_api_key=provider_values.get("openai_api_key", ""),
            local_device=provider_values.get("local_device", "cpu") or "cpu",
            local_compute_type=(
                provider_values.get("local_compute_type", "int8") or "int8"
            ),
            input_device_index=self._selected_input_device_index(),
        )

    def _choose_audio_file(self) -> None:
        if self._provider != "local":
            messagebox.showerror(
                "Local provider required",
                "Audio-file transcription currently requires the local provider.",
            )
            return

        config = self._current_config()
        if config is None:
            return
        source_name = filedialog.askopenfilename(
            title="Choose an audio file",
            filetypes=(
                ("Audio files", "*.m4a *.mp3 *.wav *.aac *.flac *.ogg *.opus"),
                ("All files", "*.*"),
            ),
        )
        if not source_name:
            return

        source = Path(source_name)
        output_name = filedialog.asksaveasfilename(
            title="Save transcript",
            initialdir=str(source.parent),
            initialfile=f"{source.stem}.txt",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            confirmoverwrite=True,
        )
        if not output_name:
            return

        self.file_button.configure(state="disabled")
        self.status_var.set(f"Transcribing {source.name} locally...")
        worker = threading.Thread(
            target=self._transcribe_file_worker,
            args=(source, Path(output_name), config, self.speaker_labels_var.get()),
            name="speech-to-text-file-transcription",
            daemon=True,
        )
        worker.start()

    def _transcribe_file_worker(
        self,
        source: Path,
        output: Path,
        config: AppConfig,
        identify_speakers: bool,
    ) -> None:
        try:
            from .file_transcription import save_transcript, transcribe_audio_file

            transcript = transcribe_audio_file(
                source,
                config,
                identify_speakers=identify_speakers,
            )
            saved_path = save_transcript(transcript, output, overwrite=True)
            self._events.put(("file_done", (transcript.text, saved_path)))
        except Exception as error:  # noqa: BLE001
            self._events.put(("file_error", str(error)))

    def _on_language_selected(self, _event: object) -> None:
        if self._provider != "local":
            return

        language_code = language_code_for_selection(self.language_var.get())
        selected_model = self.model_var.get().strip() or self._provider_profile.default_model

        if language_code.lower().startswith("en"):
            if (
                self._automatic_local_model_pair is not None
                and selected_model == self._automatic_local_model_pair[1]
            ):
                self.model_var.set(self._automatic_local_model_pair[0])
            self._automatic_local_model_pair = None
            return

        compatible_model = compatible_local_model(selected_model, language_code)
        if compatible_model != selected_model:
            self._automatic_local_model_pair = (
                selected_model,
                compatible_model,
            )
            self.model_var.set(compatible_model)
        elif (
            self._automatic_local_model_pair is not None
            and selected_model != self._automatic_local_model_pair[1]
        ):
            self._automatic_local_model_pair = None

    def _selected_input_device_index(self) -> int | None:
        if len(self._usb_microphones) <= 1:
            return None

        selected_label = self.microphone_var.get()
        for device in self._usb_microphones:
            if device.label == selected_label:
                return device.index
        return None

    def _stop_session(self) -> None:
        if self._session is not None:
            self._session.stop_recording()

        if self._recording_indicator is not None:
            self._recording_indicator.show_transcribing()
        if self._recording_meter is not None:
            self._recording_meter.hide()
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
                    "Transcript copied to the clipboard.",
                    "Transcript pasted into the focused app and copied to the clipboard.",
                } or payload.startswith("Error:") or payload.startswith(
                    "Transcription failed:"
                ) or payload.startswith("Typing failed:"):
                    self._hide_recording_meter()
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    if self._session is not None and not self._session.recording:
                        self._session = None
            elif event_type == "toggle":
                self._toggle_recording()
            elif event_type == "final":
                self._append_final_text(payload)
            elif event_type == "level":
                self._update_recording_meter(float(payload))
            elif event_type == "file_done":
                transcript, saved_path = payload
                self._clear_final_text()
                if transcript:
                    self._append_final_text(str(transcript))
                self.file_button.configure(state="normal")
                self.status_var.set(f"Transcript saved to {saved_path}")
            elif event_type == "file_error":
                self.file_button.configure(state="normal")
                self.status_var.set(f"File transcription failed: {payload}")
                messagebox.showerror("File transcription failed", str(payload))

        self.after(100, self._pump_events)

    def _append_final_text(self, text: str) -> None:
        self.final_text.configure(state="normal")
        self.final_text.insert("end", f"{text}\n")
        self.final_text.see("end")
        self.final_text.configure(state="disabled")

    def _clear_final_text(self) -> None:
        self.final_text.configure(state="normal")
        self.final_text.delete("1.0", "end")
        self.final_text.configure(state="disabled")

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

    def _configured_hotkeys(self) -> tuple[str, ...]:
        primary_hotkey = self.hotkey_var.get().strip() or self._DEFAULT_HOTKEY
        if (
            sys.platform != "darwin"
            or primary_hotkey.lower() == self._MACOS_SECONDARY_HOTKEY
        ):
            return (primary_hotkey,)
        return (primary_hotkey, self._MACOS_SECONDARY_HOTKEY)

    def _stop_hotkey_listeners(self) -> None:
        for listener in self._hotkey_listeners:
            listener.stop()
        self._hotkey_listeners.clear()

    def _restore_recording_target(self) -> None:
        if self._session is None or not self._session.recording:
            return
        self._session.restore_target_focus()

    def _start_hotkey_listener(self) -> None:
        hotkeys = self._configured_hotkeys()
        self._stop_hotkey_listeners()

        try:
            listener = build_hotkey_listener(
                hotkey=hotkeys if sys.platform == "darwin" else hotkeys[0],
                callback=lambda: self._events.put(("toggle", "")),
                release_callback=None,
            )
            self._hotkey_listeners.append(listener)
            listener.start()
            hotkey_text = " or ".join(hotkeys)
            self.status_var.set(
                f"Idle. Press {hotkey_text} to start or stop recording."
            )
        except HotkeyError as error:
            self._stop_hotkey_listeners()
            self.status_var.set(f"Hotkey unavailable: {error}")

    def _show_recording_meter(self) -> None:
        if self._recording_meter is not None:
            self._recording_meter.show()
        self._recording_indicator.show_recording(
            self.hotkey_var.get().strip() or self._DEFAULT_HOTKEY
        )

    def _hide_recording_meter(self) -> None:
        if self._recording_meter is not None:
            self._recording_meter.hide()
        self._recording_indicator.hide()

    def _update_recording_meter(self, level: float) -> None:
        if self._recording_meter is not None:
            self._recording_meter.update_level(level)
        self._recording_indicator.update_level(level)

    def _on_close(self) -> None:
        self._stop_hotkey_listeners()
        if self._session is not None:
            self._session.close()
            self._session = None
        self._recording_indicator.close()
        if self._recording_meter is not None:
            self._recording_meter.close()
            self._recording_meter = None
        self.destroy()


def main() -> None:
    app = DictationApp()
    app.mainloop()
