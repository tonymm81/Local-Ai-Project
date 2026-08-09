import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb

DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class AgentDialog(tk.Toplevel):
    def __init__(self, parent, agents, title="Choose agent", initial=False, theme_dark=True):
        super().__init__(parent)
        self.parent = parent
        self.agents = list(agents)  # lista avaimista tai nimiä
        self.selected = None
        self.initial = initial

        # Perusasetukset
        if theme_dark:
            self.configure(bg=DARK_BG)
        self.title(title)
        self.transient(parent)
        self.grab_set()

        # UI
        frame = tk.Frame(self, bg=DARK_BG if theme_dark else None, padx=12, pady=8)
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="Please choose agent", bg=DARK_BG if theme_dark else None, fg=DARK_FG if theme_dark else None)
        lbl.pack(anchor="w", pady=(0,8))

        self.var = tk.StringVar(value=self.agents[0] if self.agents else "")

        for item in self.agents:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                aid, display = item[0], item[1]
            else:
                aid, display = item, item
            rb = tk.Radiobutton(frame, text=display, variable=self.var, value=aid,
                                bg=DARK_BG if theme_dark else None,
                                fg=DARK_FG if theme_dark else None,
                                selectcolor=DARK_PANEL if theme_dark else None,
                                anchor="w")
            rb.pack(fill="x", anchor="w", pady=2)

        btn_frame = tk.Frame(frame, bg=DARK_BG if theme_dark else None)
        btn_frame.pack(fill="x", pady=(10,0))
        ok_btn = tb.Button(btn_frame, text="OK", bootstyle="primary", command=self._on_ok)
        ok_btn.pack(side="left", padx=(0,6))
        cancel_btn = tb.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self._on_cancel)
        cancel_btn.pack(side="left")

        # Jos halutaan synkroninen modal‑käyttäytys
        if self.initial:
            self.wait_window(self)

    def _on_ok(self):
        self.selected = self.var.get()
        self.destroy()

    def _on_cancel(self):
        self.selected = None
        self.destroy()

    def show(self):
        """Avaa dialogin modaalisesti ja palauttaa valitun agentin tai None."""
        # Jos ei oltu jo wait_windowissa konstruktorissa
        if not self.initial:
            self.wait_window(self)
        return self.selected
