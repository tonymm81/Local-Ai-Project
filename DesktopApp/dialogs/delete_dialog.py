import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb

# Teemavärit samaan tyyliin kuin muut dialogit
DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class DeleteDialog(tk.Toplevel):
    """
    Modal dialog joka kysyy vahvistuksen aiheen poistolle.
    Palauttaa True jos poistetaan, False jos peruutetaan.
    """
    def __init__(self, parent, agent_name: str, topic: str, theme_dark: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.agent_name = agent_name
        self.topic = topic
        self.result = False
        self.theme_dark = theme_dark

        if self.theme_dark:
            self.configure(bg=DARK_BG)

        self.title("Delete topic")
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=DARK_BG if self.theme_dark else None, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        msg = f"Delete all conversations for topic '{self.topic}'?"
        lbl = tk.Label(frame, text=msg, bg=DARK_BG if self.theme_dark else None, fg=DARK_FG if self.theme_dark else None, wraplength=420, justify="left")
        lbl.pack(anchor="w", pady=(0,12))

        btn_frame = tk.Frame(frame, bg=DARK_BG if self.theme_dark else None)
        btn_frame.pack(fill="x")

        tb.Button(btn_frame, text="Delete", bootstyle="danger", command=self._on_delete).pack(side="left", padx=(0,6))
        tb.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self._on_cancel).pack(side="left")

        # Modal wait
        self.wait_window(self)

    def _on_delete(self):
        self.result = True
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self.destroy()

    def show(self):
        """Palauttaa True jos käyttäjä vahvisti poiston, muuten False."""
        return self.result
