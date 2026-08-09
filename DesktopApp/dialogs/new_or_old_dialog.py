import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb

DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class NewOrOldDialog(tk.Toplevel):
    """
    Modal dialog joka kysyy, aloittaako uuden keskustelun vai jatkaako vanhaa.
    Jos valitaan uusi, dialog palauttaa ("new", topic_str).
    Jos valitaan vanha, dialog palauttaa ("old", None).
    Jos suljetaan/peruutetaan, palauttaa (None, None).
    """
    def __init__(self, parent, theme_dark: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.theme_dark = theme_dark
        self.result = (None, None)

        if self.theme_dark:
            self.configure(bg=DARK_BG)

        self.title("New or existing conversation")
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=DARK_BG if self.theme_dark else None, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        self.choice = tk.StringVar(value="new")
        tk.Radiobutton(frame, text="New conversation", variable=self.choice, value="new",
                       bg=DARK_BG if self.theme_dark else None,
                       fg=DARK_FG if self.theme_dark else None,
                       selectcolor=DARK_PANEL if self.theme_dark else None).pack(anchor="w", padx=12, pady=4)
        tk.Radiobutton(frame, text="Continue existing", variable=self.choice, value="old",
                       bg=DARK_BG if self.theme_dark else None,
                       fg=DARK_FG if self.theme_dark else None,
                       selectcolor=DARK_PANEL if self.theme_dark else None).pack(anchor="w", padx=12, pady=4)

        self.topic_entry = tk.Entry(frame, bg=DARK_PANEL if self.theme_dark else "white",
                                    fg=DARK_FG if self.theme_dark else "black", insertbackground=DARK_FG if self.theme_dark else "black")
        self.topic_entry.pack(fill="x", padx=12, pady=6)
        self.topic_entry.insert(0, "If new, enter topic here")

        btn_frame = tk.Frame(frame, bg=DARK_BG if self.theme_dark else None)
        btn_frame.pack(fill="x", pady=(6,0))
        tb.Button(btn_frame, text="OK", bootstyle="primary", command=self._on_ok).pack(side="left", padx=6)
        tb.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self._on_cancel).pack(side="left")

        # modal wait
        self.wait_window(self)

    def _on_ok(self):
        sel = self.choice.get()
        if sel == "new":
            topic = self.topic_entry.get().strip()
            if not topic:
                messagebox.showerror("Error", "Topic required for new conversation")
                return
            self.result = ("new", topic)
        else:
            self.result = ("old", None)
        self.destroy()

    def _on_cancel(self):
        self.result = (None, None)
        self.destroy()

    def show(self):
        """Palauttaa tuple (mode, topic). mode in {"new","old",None}"""
        return self.result
