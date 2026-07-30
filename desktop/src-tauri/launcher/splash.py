"""Splash screen — startup progress window."""

import tkinter as tk
from tkinter import ttk


class SplashScreen:
    def __init__(self):
        self._root = tk.Tk()
        self._root.title("Eve OS")
        self._root.overrideredirect(True)
        self._root.configure(bg="#1a1a2e")
        self._root.attributes("-topmost", True)
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w, h = 420, 320
        x, y = (sw - w) // 2, (sh - h) // 2
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._items = []
        self._build_ui()
        self._root.update()

    def _build_ui(self):
        title = tk.Label(
            self._root, text="Eve OS",
            font=("Segoe UI", 28, "bold"),
            fg="#e94560", bg="#1a1a2e",
        )
        title.pack(pady=(40, 5))
        subtitle = tk.Label(
            self._root, text="Starting...",
            font=("Segoe UI", 10),
            fg="#a0a0b0", bg="#1a1a2e",
        )
        subtitle.pack(pady=(0, 20))
        self._progress = ttk.Progressbar(
            self._root, mode="indeterminate", length=300,
        )
        self._progress.pack(pady=(0, 20))
        self._progress.start(10)
        self._status_frame = tk.Frame(self._root, bg="#1a1a2e")
        self._status_frame.pack(fill="both", expand=True, padx=40)

    def update_status(self, step: str):
        color = "#4ecca3" if not step.startswith("✗") else "#e94560"
        prefix = "✓" if not step.startswith("✗") else "✗"
        display = step if step.startswith("✗") or step.startswith("✓") else f"{prefix} {step}"
        lbl = tk.Label(
            self._status_frame, text=display,
            font=("Consolas", 10), fg=color, bg="#1a1a2e",
            anchor="w",
        )
        lbl.pack(fill="x", pady=1)
        self._items.append(lbl)
        self._root.update()

    def set_ready(self):
        self._progress.stop()
        self._progress.destroy()
        lbl = tk.Label(
            self._status_frame, text="✓ Ready",
            font=("Consolas", 12, "bold"),
            fg="#4ecca3", bg="#1a1a2e",
        )
        lbl.pack(pady=(10, 0))
        self._root.update()

    def close(self):
        self._root.destroy()
