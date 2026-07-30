"""First-run setup wizard — API keys, theme, provider selection."""

import tkinter as tk
from launcher.config import LauncherConfig


class FirstRunWizard:
    def __init__(self, config: LauncherConfig):
        self._config = config
        self._root = tk.Tk()
        self._root.title("Welcome to Eve OS")
        self._root.configure(bg="#1a1a2e")
        self._root.resizable(False, False)
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w, h = 600, 500
        x, y = (sw - w) // 2, (sh - h) // 2
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._frame = tk.Frame(self._root, bg="#1a1a2e")
        self._frame.pack(fill="both", expand=True, padx=20, pady=20)
        self._step = 0
        self._result = False
        self._show_step(0)

    def _clear(self):
        for w in self._frame.winfo_children():
            w.destroy()

    def _show_step(self, step: int):
        self._clear()
        if step == 0:
            self._step_welcome()
        elif step == 1:
            self._step_providers()
        elif step == 2:
            self._step_theme()
        elif step == 3:
            self._step_finish()
        self._root.update()

    def _step_welcome(self):
        tk.Label(
            self._frame, text="Welcome to Eve OS",
            font=("Segoe UI", 22, "bold"), fg="#e94560", bg="#1a1a2e",
        ).pack(pady=(30, 10))
        tk.Label(
            self._frame,
            text="Your intelligent desktop assistant.\nLet's get you set up.",
            font=("Segoe UI", 11), fg="#a0a0b0", bg="#1a1a2e",
            justify="center",
        ).pack(pady=(0, 30))
        tk.Button(
            self._frame, text="Get Started", font=("Segoe UI", 12),
            bg="#e94560", fg="white", padx=30, pady=6, relief="flat",
            cursor="hand2",
            command=lambda: self._show_step(1),
        ).pack(pady=10)

    def _step_providers(self):
        tk.Label(
            self._frame, text="AI Providers",
            font=("Segoe UI", 18, "bold"), fg="#e94560", bg="#1a1a2e",
        ).pack(pady=(20, 5))
        tk.Label(
            self._frame,
            text="Configure which AI providers to use.\nAPI keys can be added later in Settings.",
            font=("Segoe UI", 10), fg="#a0a0b0", bg="#1a1a2e",
            justify="center",
        ).pack(pady=(0, 15))
        self._provider_vars = {}
        providers = [
            ("gemini", "Gemini (Google)", True),
            ("groq", "Groq", True),
            ("openrouter", "OpenRouter", True),
            ("ollama", "Ollama (Local)", False),
            ("github_models", "GitHub Models", True),
            ("z_ai", "Z.ai", True),
        ]
        for key, label, needs_key in providers:
            var = tk.BooleanVar(value=key == "ollama")
            cb = tk.Checkbutton(
                self._frame, text=label, variable=var,
                fg="white", bg="#1a1a2e", selectcolor="#16213e",
                activebackground="#1a1a2e", activeforeground="white",
                font=("Segoe UI", 10),
            )
            cb.pack(anchor="w", pady=2)
            self._provider_vars[key] = var
        tk.Button(
            self._frame, text="Next", font=("Segoe UI", 12),
            bg="#e94560", fg="white", padx=30, pady=6, relief="flat",
            cursor="hand2",
            command=self._save_providers,
        ).pack(pady=15)

    def _save_providers(self):
        providers = self._config.get("ai_providers", {})
        for key, var in self._provider_vars.items():
            if key in providers:
                providers[key]["enabled"] = var.get()
        self._config.set("ai_providers", providers)
        self._show_step(2)

    def _step_theme(self):
        tk.Label(
            self._frame, text="Choose Theme",
            font=("Segoe UI", 18, "bold"), fg="#e94560", bg="#1a1a2e",
        ).pack(pady=(20, 15))
        self._theme_var = tk.StringVar(value=self._config.get("theme", "system"))
        for val, label in [("dark", "Dark"), ("light", "Light"), ("system", "System Default")]:
            rb = tk.Radiobutton(
                self._frame, text=label, variable=self._theme_var, value=val,
                fg="white", bg="#1a1a2e", selectcolor="#16213e",
                activebackground="#1a1a2e", activeforeground="white",
                font=("Segoe UI", 11),
            )
            rb.pack(anchor="w", pady=4)
        tk.Button(
            self._frame, text="Next", font=("Segoe UI", 12),
            bg="#e94560", fg="white", padx=30, pady=6, relief="flat",
            cursor="hand2",
            command=lambda: [
                self._config.set("theme", self._theme_var.get()),
                self._show_step(3),
            ],
        ).pack(pady=15)

    def _step_finish(self):
        tk.Label(
            self._frame, text="Setup Complete",
            font=("Segoe UI", 18, "bold"), fg="#4ecca3", bg="#1a1a2e",
        ).pack(pady=(20, 10))
        tk.Label(
            self._frame,
            text="✓ Configuration saved\n✓ Theme selected\n✓ Providers configured",
            font=("Segoe UI", 11), fg="#a0a0b0", bg="#1a1a2e",
            justify="center",
        ).pack(pady=(0, 20))
        tk.Label(
            self._frame,
            text="You can change these settings anytime from the tray menu.",
            font=("Segoe UI", 10), fg="#666680", bg="#1a1a2e",
        ).pack(pady=(0, 20))
        tk.Button(
            self._frame, text="Launch Eve", font=("Segoe UI", 14, "bold"),
            bg="#4ecca3", fg="#1a1a2e", padx=40, pady=8, relief="flat",
            cursor="hand2",
            command=self._finish,
        ).pack(pady=10)

    def _finish(self):
        self._config.set("first_run", False)
        self._result = True
        self._root.destroy()

    def run(self) -> bool:
        self._root.mainloop()
        return self._result
