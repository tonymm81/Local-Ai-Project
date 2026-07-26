import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as tb

# Teemavärit (sama kuin muualla projektissa)
DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class AnalyticsView(tk.Toplevel):
    """
    Yksinkertainen analytics‑view joka avautuu modaalisesti ja näyttää tekstiä.
    Palauttaa None kun suljetaan.
    """
    def __init__(self, parent, analytics_text: str = None, theme_dark: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.analytics_text = analytics_text or "Analytics data (dummy)\n\nSentiment: Neutral\nTokens: 123\nConfidence: 0.87"
        self.theme_dark = theme_dark

        if self.theme_dark:
            self.configure(bg=DARK_BG)

        self.title("Analytics")
        self.transient(parent)
        self.grab_set()

        # Content frame
        frame = tk.Frame(self, bg=DARK_BG if self.theme_dark else None, padx=8, pady=8)
        frame.pack(fill="both", expand=True)

        # ScrolledText (manuaalisesti väritys koska ScrolledText on tk-widget)
        txt = scrolledtext.ScrolledText(frame, height=20,
                                       bg=DARK_PANEL if self.theme_dark else "white",
                                       fg=DARK_FG if self.theme_dark else "black",
                                       insertbackground=DARK_FG if self.theme_dark else "black",
                                       wrap="word")
        txt.pack(fill="both", expand=True, padx=4, pady=4)
        txt.insert("end", self.analytics_text)
        txt.config(state="disabled")

        # Back / Close -nappi
        btn_frame = tk.Frame(frame, bg=DARK_BG if self.theme_dark else None)
        btn_frame.pack(fill="x", pady=(6,8))
        tb.Button(btn_frame, text="Back", bootstyle="secondary", command=self._on_close).pack(side="right", padx=6)

        # Modal wait
        self.wait_window(self)

    def _on_close(self):
        self.destroy()
