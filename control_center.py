#!/usr/bin/env python3
"""TIRIAS Control Center v0.6 — a local Tkinter interface for TIRIAS Core."""
from __future__ import annotations

from datetime import datetime
import json
import threading
import tkinter as tk
from pynput import keyboard
from tkinter import messagebox, ttk
from pathlib import Path
import sys

from main import (
    VERSION,
    TIRIASCore,
    VoiceInputError,
    dispatch_voice_transcript,
    is_listen_request,
)

BG = "#0b1020"
PANEL = "#121a2d"
PANEL_ALT = "#17223a"
BORDER = "#26334d"
TEXT = "#edf3ff"
MUTED = "#94a3bd"
ACCENT = "#35d9ce"
BLUE = "#6ba8ff"
GREEN = "#72e0a3"
AMBER = "#f6c76d"
RED = "#ff8585"


class TIRIASControlCenter:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.core = TIRIASCore()
        self.busy = False
        self.speech_lock = threading.Lock()
        self.history_path = Path.home() / ".local/state/tirias/control_center_history.jsonl"
        self.history: list[dict[str, str]] = []
        self._load_history()

        root.title(f"TIRIAS Control Center {VERSION}")
        root.geometry("1120x800")
        root.minsize(920, 680)
        root.configure(bg=BG)
        self._configure_styles()
        self._build_ui()
        self.refresh_status()
        self.hotkey_listener = None
        self.right_ctrl_down = False
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._start_hotkey_listener()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL_ALT, foreground=MUTED,
                        padding=(18, 10), font=("TkDefaultFont", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=30, borderwidth=0,
                        font=("TkDefaultFont", 9))
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=MUTED,
                        padding=(8, 7), font=("TkDefaultFont", 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", "#24415a")],
                  foreground=[("selected", TEXT)])
        style.configure("Vertical.TScrollbar", background=PANEL_ALT,
                        troughcolor=PANEL, bordercolor=PANEL, arrowcolor=MUTED)

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG, padx=26, pady=20)
        header.pack(fill="x")
        title_row = tk.Frame(header, bg=BG)
        title_row.pack(fill="x")
        mark = tk.Canvas(title_row, width=46, height=46, bg=BG, highlightthickness=0)
        mark.pack(side="left", padx=(0, 13))
        mark.create_oval(4, 4, 42, 42, outline=ACCENT, width=2)
        mark.create_line(13, 28, 22, 13, 31, 28, fill=ACCENT, width=2, smooth=True)
        mark.create_line(15, 25, 29, 25, fill=BLUE, width=2)
        title_block = tk.Frame(title_row, bg=BG)
        title_block.pack(side="left", anchor="w")
        tk.Label(title_block, text="TIRIAS", bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 23, "bold")).pack(anchor="w")
        tk.Label(title_block, text="PERSONAL AI SYSTEM  /  LOCAL CONTROL CENTER",
                 bg=BG, fg=MUTED, font=("TkFixedFont", 9)).pack(anchor="w", pady=(1, 0))
        self.online_badge = tk.Label(title_row, text="●  CORE ONLINE", bg="#173c38", fg=GREEN,
                                     font=("TkDefaultFont", 9, "bold"), padx=13, pady=8)
        self.online_badge.pack(side="right", anchor="center")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=26)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=26, pady=(15, 20))
        self.dashboard = tk.Frame(self.notebook, bg=BG)
        self.history_tab = tk.Frame(self.notebook, bg=BG)
        self.settings_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.dashboard, text="  Overview  ")
        self.notebook.add(self.history_tab, text="  Command History  ")
        self.notebook.add(self.settings_tab, text="  Voice & Settings  ")
        self._build_dashboard()
        self._build_history_tab()
        self._build_settings_tab()

        footer = tk.Frame(self.root, bg=BG, padx=26, pady=0)
        footer.pack(fill="x", pady=(0, 12))
        tk.Label(footer, text="OFFLINE-FIRST  •  PUSH-TO-TALK  •  APPROVED ACTIONS ONLY",
                 bg=BG, fg=MUTED, font=("TkFixedFont", 8)).pack(side="left")
        tk.Label(footer, text=VERSION.upper(), bg=BG, fg=ACCENT,
                 font=("TkFixedFont", 8, "bold")).pack(side="right")

    def _card(self, parent, title, value="", detail="", accent=ACCENT):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1,
                         padx=15, pady=13)
        tk.Label(frame, text=title.upper(), bg=PANEL, fg=MUTED,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        value_label = tk.Label(frame, text=value, bg=PANEL, fg=accent,
                               font=("TkDefaultFont", 14, "bold"), anchor="w")
        value_label.pack(anchor="w", pady=(8, 4))
        detail_label = tk.Label(frame, text=detail, bg=PANEL, fg=MUTED,
                                font=("TkDefaultFont", 8), anchor="w", justify="left",
                                wraplength=220)
        detail_label.pack(anchor="w", fill="x")
        return frame, value_label, detail_label

    def _button(self, parent, label, command, *, primary=False, danger=False, compact=False):
        bg = ACCENT if primary else ("#42252f" if danger else PANEL_ALT)
        fg = BG if primary else (RED if danger else TEXT)
        active_bg = "#70e8df" if primary else ("#52313d" if danger else "#223451")
        padx, pady = ((14, 9) if not compact else (10, 7))
        return tk.Button(parent, text=label, command=command, bg=bg, fg=fg,
                         activebackground=active_bg, activeforeground=fg,
                         disabledforeground="#60708a", relief="flat", bd=0,
                         padx=padx, pady=pady, cursor="hand2",
                         font=("TkDefaultFont", 9, "bold"), takefocus=True)

    def _section_title(self, parent, title, subtitle=None):
        block = tk.Frame(parent, bg=BG)
        tk.Label(block, text=title, bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(block, text=subtitle, bg=BG, fg=MUTED,
                     font=("TkDefaultFont", 9)).pack(anchor="w", pady=(3, 0))
        return block

    def _build_dashboard(self):
        dash = self.dashboard
        cards = tk.Frame(dash, bg=BG)
        cards.pack(fill="x", pady=(1, 14))
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cards")
        self.core_card, self.core_value, self.core_detail = self._card(
            cards, "Core status", "ONLINE", "Command router ready", GREEN)
        self.input_card, self.input_value, self.input_detail = self._card(
            cards, "Voice input", "CHECKING", "Offline speech recognition")
        self.output_card, self.output_value, self.output_detail = self._card(
            cards, "Spoken replies", "CHECKING", "eSpeak NG")
        self.folder_card, self.folder_value, self.folder_detail = self._card(
            cards, "Working folder", "HOME", str(self.core.current_dir), BLUE)
        for i, card in enumerate((self.core_card, self.input_card, self.output_card, self.folder_card)):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 3 else 7))

        main_row = tk.Frame(dash, bg=BG)
        main_row.pack(fill="both", expand=True)
        main_row.grid_columnconfigure(0, weight=3, uniform="main")
        main_row.grid_columnconfigure(1, weight=2, uniform="main")
        main_row.grid_rowconfigure(0, weight=1)

        console = tk.Frame(main_row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1,
                           padx=16, pady=15)
        console.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._section_title(console, "Command console", "Type a command or use push-to-talk.").pack(anchor="w")
        command_row = tk.Frame(console, bg=PANEL)
        command_row.pack(fill="x", pady=(14, 8))
        self.command_var = tk.StringVar()
        self.command_entry = tk.Entry(command_row, textvariable=self.command_var, bg="#0d1425",
                                      fg=TEXT, insertbackground=ACCENT, relief="flat",
                                      highlightthickness=1, highlightbackground=BORDER,
                                      highlightcolor=ACCENT, font=("TkDefaultFont", 11))
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.command_entry.bind("<Return>", lambda _event: self.submit_command())
        self.run_button = self._button(command_row, "RUN  ↗", self.submit_command, primary=True)
        self.run_button.pack(side="right")
        controls = tk.Frame(console, bg=PANEL)
        controls.pack(fill="x", pady=(0, 12))
        self.listen_button = self._button(controls, "●  LISTEN", self.start_listening, primary=True)
        self.listen_button.pack(side="left")
        self.cancel_button = self._button(controls, "CANCEL ACTION", lambda: self.execute("cancel"), danger=True, compact=True)
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.busy_label = tk.Label(controls, text="Ready for your command", bg=PANEL, fg=GREEN,
                                   font=("TkDefaultFont", 9))
        self.busy_label.pack(side="right", padx=(5, 0))

        tk.Label(console, text="LATEST RESPONSE", bg=PANEL, fg=MUTED,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w", pady=(1, 6))
        response_frame = tk.Frame(console, bg="#0d1425", highlightbackground=BORDER, highlightthickness=1)
        response_frame.pack(fill="both", expand=True)
        self.response_text = tk.Text(response_frame, bg="#0d1425", fg=TEXT,
                                     insertbackground=ACCENT, relief="flat", wrap="word",
                                     font=("TkDefaultFont", 10), padx=12, pady=12,
                                     height=7, state="disabled")
        response_scroll = ttk.Scrollbar(response_frame, orient="vertical", command=self.response_text.yview)
        self.response_text.configure(yscrollcommand=response_scroll.set)
        self.response_text.pack(side="left", fill="both", expand=True)
        response_scroll.pack(side="right", fill="y")
        self.response_text.configure(state="normal")
        self.response_text.insert("end", "TIRIAS Control Center ready. Try ‘What time is it?’ or press LISTEN and speak a supported command.")
        self.response_text.configure(state="disabled")

        quick = tk.Frame(main_row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1,
                         padx=15, pady=15)
        quick.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._section_title(quick, "Quick actions", "These use TIRIAS's existing approved commands.").pack(anchor="w")
        quick_grid = tk.Frame(quick, bg=PANEL)
        quick_grid.pack(fill="x", pady=(14, 10))
        actions = [
            ("What time?", "what time is it"),
            ("System status", "show me system info"),
            ("List files", "list files"),
            ("Disk space", "check disk space"),
            ("Open terminal", "open a terminal"),
            ("Open browser", "launch my browser"),
            ("Workspace", "open workspace"),
            ("Confirm action", "confirm"),
        ]
        for index, (label, command) in enumerate(actions):
            button = self._button(quick_grid, label, lambda c=command: self.execute(c), compact=True,
                                  primary=(label == "System status"))
            button.grid(row=index // 2, column=index % 2, sticky="ew",
                        padx=(0, 5 if index % 2 == 0 else 0), pady=4)
        quick_grid.grid_columnconfigure((0, 1), weight=1, uniform="actions")
        tk.Frame(quick, bg=BORDER, height=1).pack(fill="x", pady=(5, 12))
        tk.Label(quick, text="SAFETY STATE", bg=PANEL, fg=MUTED,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        self.pending_label = tk.Label(quick, text="No pending action", bg=PANEL, fg=GREEN,
                                      font=("TkDefaultFont", 10, "bold"))
        self.pending_label.pack(anchor="w", pady=(6, 4))
        tk.Label(quick, text="Folder creation requires confirmation. Arbitrary shell commands are not executed.",
                 bg=PANEL, fg=MUTED, wraplength=300, justify="left",
                 font=("TkDefaultFont", 8)).pack(anchor="w")

    def _build_history_tab(self):
        tab = self.history_tab
        intro = self._section_title(tab, "Command history", "Recent typed and recognized commands are stored locally on this computer.")
        intro.pack(anchor="w", pady=(8, 14))
        bar = tk.Frame(tab, bg=BG)
        bar.pack(fill="x", pady=(0, 8))
        self._button(bar, "REFRESH", self.refresh_history, compact=True).pack(side="left")
        self._button(bar, "CLEAR HISTORY", self.clear_history, danger=True, compact=True).pack(side="right")
        table_frame = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True)
        columns = ("time", "source", "command", "response")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"time": "TIME", "source": "SOURCE", "command": "COMMAND", "response": "RESPONSE"}
        widths = {"time": 145, "source": 80, "command": 225, "response": 460}
        for name in columns:
            self.history_tree.heading(name, text=headings[name])
            self.history_tree.column(name, width=widths[name], minwidth=70,
                                     stretch=(name in ("command", "response")))
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.history_tree.bind("<Double-1>", self.show_history_detail)
        self.refresh_history()

    def _build_settings_tab(self):
        tab = self.settings_tab
        self._section_title(tab, "Voice & settings", "Control speech output and inspect the local microphone setup.").pack(anchor="w", pady=(8, 14))
        grid = tk.Frame(tab, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure((0, 1), weight=1, uniform="settings")
        speech = tk.Frame(grid, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=17)
        speech.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        mic = tk.Frame(grid, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=17)
        mic.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        privacy = tk.Frame(grid, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=17)
        privacy.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        self._section_title(speech, "Spoken responses", "Uses local eSpeak NG when available.").pack(anchor="w")
        self.speech_state_label = tk.Label(speech, text="Checking speech engine…", bg=PANEL, fg=MUTED,
                                           font=("TkDefaultFont", 10, "bold"))
        self.speech_state_label.pack(anchor="w", pady=(17, 12))
        speech_buttons = tk.Frame(speech, bg=PANEL)
        speech_buttons.pack(anchor="w")
        self._button(speech_buttons, "VOICE ON", lambda: self.execute("voice on"), primary=True).pack(side="left")
        self._button(speech_buttons, "VOICE OFF", lambda: self.execute("voice off"), compact=True).pack(side="left", padx=(8, 0))

        self._section_title(mic, "Microphone input", "Push-to-talk only; TIRIAS does not listen continuously.").pack(anchor="w")
        self.mic_state_label = tk.Label(mic, text="Checking microphone model…", bg=PANEL, fg=MUTED,
                                        wraplength=360, justify="left", font=("TkDefaultFont", 10, "bold"))
        self.mic_state_label.pack(anchor="w", pady=(17, 12))
        mic_buttons = tk.Frame(mic, bg=PANEL)
        mic_buttons.pack(anchor="w")
        self._button(mic_buttons, "CHECK INPUT", lambda: self.execute("voice input status"), primary=True).pack(side="left")
        self._button(mic_buttons, "LIST DEVICES", lambda: self.execute("voice devices"), compact=True).pack(side="left", padx=(8, 0))
        self._button(mic_buttons, "TEST LISTEN", self.start_listening, compact=True).pack(side="left", padx=(8, 0))

        self._section_title(privacy, "Local processing & permissions").pack(anchor="w")
        tk.Label(privacy,
                 text="Speech recognition uses the local Vosk model and processes microphone audio in memory. "
                      "The Control Center saves command text and responses to a local history file so you can review them; "
                      "no audio recordings are saved. Use CLEAR HISTORY on the Command History tab to remove that history.",
                 bg=PANEL, fg=MUTED, wraplength=900, justify="left",
                 font=("TkDefaultFont", 9)).pack(anchor="w", pady=(10, 0))

    def _load_history(self):
        try:
            with self.history_path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        item = json.loads(line)
                        if all(key in item for key in ("time", "source", "command", "response")):
                            self.history.append({k: str(item[k]) for k in ("time", "source", "command", "response")})
                    except (ValueError, TypeError):
                        continue
        except OSError:
            pass
        self.history = self.history[-200:]

    def _record_history(self, source, command, response):
        item = {
            "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "source": source,
            "command": str(command),
            "response": str(response),
        }
        self.history.append(item)
        self.history = self.history[-200:]
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with self.history_path.open("w", encoding="utf-8") as stream:
                for entry in self.history:
                    stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            self._set_response("Command completed, but TIRIAS could not save local command history.")
        self.refresh_history()

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for idx, item in enumerate(reversed(self.history)):
            self.history_tree.insert("", "end", iid=f"h{idx}", values=(
                item["time"], item["source"], item["command"], item["response"].replace("\n", " · ")
            ))

    def clear_history(self):
        if not messagebox.askyesno("Clear command history", "Delete the locally saved TIRIAS Control Center command history?", parent=self.root):
            return
        self.history.clear()
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            self.history_path.write_text("", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Unable to clear history", str(exc), parent=self.root)
        self.refresh_history()

    def show_history_detail(self, _event=None):
        selection = self.history_tree.selection()
        if not selection:
            return
        index = int(selection[0][1:])
        item = list(reversed(self.history))[index]
        messagebox.showinfo("Command details", f"Time: {item['time']}\nSource: {item['source']}\n\nCommand:\n{item['command']}\n\nResponse:\n{item['response']}", parent=self.root)

    def _set_response(self, text):
        self.response_text.configure(state="normal")
        self.response_text.delete("1.0", "end")
        self.response_text.insert("end", str(text))
        self.response_text.configure(state="disabled")

    def _speak_async(self, response):
        def worker():
            with self.speech_lock:
                self.core.speak_response(response)
        threading.Thread(target=worker, daemon=True).start()

    def execute(self, command, source="button"):
        if self.busy:
            self._set_response("TIRIAS is listening right now. Wait until the microphone operation finishes.")
            return
        if is_listen_request(command):
            self.start_listening()
            return
        keep_running, response = self.core.handle_command(command)
        self._set_response(response)
        self._record_history(source, command, response)
        self.refresh_status()
        self._speak_async(response)
        if not keep_running:
            self.root.after(900, self.close)

    def submit_command(self):
        command = self.command_var.get().strip()
        if not command:
            self.command_entry.focus_set()
            return
        self.command_var.set("")
        self.execute(command, source="typed")

    def start_listening(self):
        if self.busy:
            return
        if not self.core.voice_input.ready:
            response = self.core.voice_input.status()
            self._set_response(response)
            self._record_history("system", "voice input status", response)
            self.refresh_status()
            return
        self.busy = True
        self._set_busy_ui(True)
        self._set_response(f"Listening for up to {self.core.voice_input.max_seconds} seconds. Speak one supported command…")

        def worker():
            try:
                transcript = self.core.voice_input.listen_once()
                keep_running, response = dispatch_voice_transcript(self.core, transcript)
                error = None
            except VoiceInputError as exc:
                transcript = ""
                keep_running, response, error = True, str(exc), str(exc)
            self.root.after(0, lambda: self._finish_listening(transcript, keep_running, response, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_listening(self, transcript, keep_running, response, error):
        self.busy = False
        self._set_busy_ui(False)
        command = transcript or ("microphone error" if error else "(no speech recognized)")
        source = "voice" if transcript else "system"
        self._set_response((f"Recognized: {transcript}\n\n" if transcript else "") + response)
        self._record_history(source, command, response)
        self.refresh_status()
        if transcript:
            self._speak_async(response)
        elif error:
            # Error text is visible; don't force a spoken diagnostic over a failed input.
            pass
        if not keep_running:
            self.root.after(900, self.close)

    def _set_busy_ui(self, busy):
        state = "disabled" if busy else "normal"
        self.run_button.configure(state=state)
        self.listen_button.configure(state=state, text=("●  LISTENING…" if busy else "●  LISTEN"))
        self.command_entry.configure(state=state)
        self.busy_label.configure(text=("Listening for a command…" if busy else "Ready for your command"),
                                  fg=AMBER if busy else GREEN)

    def refresh_status(self):
        if not hasattr(self, "input_value"):
            return
        voice_ready = self.core.voice_input.ready
        self.input_value.configure(text=("READY" if voice_ready else "SETUP NEEDED"),
                                   fg=(GREEN if voice_ready else AMBER))
        self.input_detail.configure(text="Local Vosk model available" if voice_ready else "Run setup_voice.sh and check model path")
        speech_available = self.core.speech.available
        speech_enabled = self.core.speech.enabled
        self.output_value.configure(text=("ON" if speech_enabled else "OFF"),
                                    fg=(GREEN if speech_enabled else MUTED))
        self.output_detail.configure(text=("eSpeak NG available" if speech_available else "eSpeak NG not installed"))
        folder_name = self.core.current_dir.name or str(self.core.current_dir)
        self.folder_value.configure(text=folder_name[:22], fg=BLUE)
        self.folder_detail.configure(text=str(self.core.current_dir))
        pending = self.core.pending
        self.pending_label.configure(text=(f"Awaiting confirmation: {pending[1]}" if pending else "No pending action"),
                                     fg=(AMBER if pending else GREEN))
        self.speech_state_label.configure(
            text=f"Engine: {'available' if speech_available else 'not installed'}  •  Responses: {'ON' if speech_enabled else 'OFF'}",
            fg=(GREEN if speech_enabled else MUTED))
        self.mic_state_label.configure(
            text=("Ready — local English recognition model loaded on first listen." if voice_ready
                  else self.core.voice_input.status()),
            fg=(GREEN if voice_ready else AMBER))
        self.online_badge.configure(text="●  CORE ONLINE", fg=GREEN, bg="#173c38")

    def _start_hotkey_listener(self):
        def on_press(key):
            if key == keyboard.Key.ctrl_r and not self.right_ctrl_down:
                self.right_ctrl_down = True
                self.root.after(0, self._hotkey_listen)

        def on_release(key):
            if key == keyboard.Key.ctrl_r:
                self.right_ctrl_down = False

        try:
            self.hotkey_listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
            )
            self.hotkey_listener.start()
            self._set_response(
                "Ready. Press Right Ctrl to speak, or use the LISTEN button."
            )
        except Exception as exc:
            self._set_response(
                f"Global shortcut unavailable ({exc}). Use the LISTEN button."
            )

    def _hotkey_listen(self):
        if self.root.winfo_exists() and not self.busy:
            self.start_listening()

    def close(self):
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
        self.root.destroy()


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print("TIRIAS Control Center couldn't open a graphical display.", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        print("Run it from your Linux desktop session, not a text-only terminal.", file=sys.stderr)
        return 1
    TIRIASControlCenter(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
