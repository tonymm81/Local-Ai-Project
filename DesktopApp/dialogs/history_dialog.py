import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb

DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class HistoryDialog(tk.Toplevel):
    """
    Modal dialog joka näyttää valitun agentin aiheet.
    Palauttaa tuple(nimi, action) missä action on "open", "delete" tai None (close).
    """
    def __init__(self, parent, agent_name: str, topics: list, theme_dark: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.agent_name = agent_name
        self.topics = topics or []
        self.selected_topic = None
        self.action = None
        self.theme_dark = theme_dark

        if self.theme_dark:
            self.configure(bg=DARK_BG)

        self.title("History topics")
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=DARK_BG if self.theme_dark else None, padx=8, pady=8)
        frame.pack(fill="both", expand=True)

        self.lb = tk.Listbox(frame, height=12,
                             bg=DARK_PANEL if self.theme_dark else "white",
                             fg=DARK_FG if self.theme_dark else "black",
                             activestyle="none")
        for t in self.topics:
            self.lb.insert("end", t)
        self.lb.pack(fill="both", expand=False, padx=4, pady=6)

        btn_frame = tk.Frame(frame, bg=DARK_BG if self.theme_dark else None)
        btn_frame.pack(fill="x", pady=(6,0))

        tb.Button(btn_frame, text="Open", bootstyle="primary", command=self._on_open).pack(side="left", padx=6)
        tb.Button(btn_frame, text="Delete topic", bootstyle="danger", command=self._on_delete).pack(side="left", padx=6)
        tb.Button(btn_frame, text="Close", bootstyle="secondary", command=self._on_close).pack(side="right", padx=6)

        # Modal wait
        self.wait_window(self)

    def _get_selection(self):
        sel = self.lb.curselection()
        if not sel:
            return None
        return self.topics[sel[0]]

    def _on_open(self):
        topic = self._get_selection()
        if not topic:
            messagebox.showinfo("Info", "Select a topic")
            return
        self.selected_topic = topic
        self.action = "open"
        self.destroy()

    def _on_delete(self):
        topic = self._get_selection()
        if not topic:
            messagebox.showinfo("Info", "Select a topic to delete")
            return
        self.selected_topic = topic
        self.action = "delete"
        self.destroy()

    def _on_close(self):
        self.selected_topic = None
        self.action = None
        self.destroy()

    def show(self):
        """Palauttaa (selected_topic, action) tai (None, None) jos suljettu."""
        return (self.selected_topic, self.action)
