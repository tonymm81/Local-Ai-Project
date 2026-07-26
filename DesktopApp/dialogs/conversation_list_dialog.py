import tkinter as tk
from tkinter import messagebox, scrolledtext
import ttkbootstrap as tb

# Teemavärit samat kuin muualla projektissa
DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"

class ConversationListDialog(tk.Toplevel):
    """
    Modal dialog joka näyttää valitun aiheen keskustelut listana.
    Palauttaa valitun keskustelun dictin tai None.
    """
    def __init__(self, parent, agent_name: str, topic: str, conversations: list, theme_dark: bool = True):
        super().__init__(parent)
        self.parent = parent
        self.agent_name = agent_name
        self.topic = topic
        self.conversations = conversations or []
        self.selected_conv = None
        self.theme_dark = theme_dark

        if self.theme_dark:
            self.configure(bg=DARK_BG)

        self.title(f"Conversations in {self.topic}")
        self.transient(parent)
        self.grab_set()

        # Layout
        frame = tk.Frame(self, bg=DARK_BG if self.theme_dark else None, padx=8, pady=8)
        frame.pack(fill="both", expand=True)

        # Listbox preview
        self.lb = tk.Listbox(frame, height=10, bg=DARK_PANEL if self.theme_dark else "white",
                             fg=DARK_FG if self.theme_dark else "black", activestyle="none")
        for c in self.conversations:
            preview = (c.get("prompt","") + " " + c.get("response",""))[:120]
            self.lb.insert("end", preview)
        self.lb.pack(fill="both", expand=False, padx=4, pady=6)

        # Optional preview pane for full content
        preview_label = tk.Label(frame, text="Preview", bg=DARK_BG if self.theme_dark else None,
                                 fg=DARK_FG if self.theme_dark else None)
        preview_label.pack(anchor="w", padx=4)
        self.preview_txt = scrolledtext.ScrolledText(frame, height=8,
                                                     bg=DARK_PANEL if self.theme_dark else "white",
                                                     fg=DARK_FG if self.theme_dark else "black",
                                                     insertbackground=DARK_FG if self.theme_dark else "black",
                                                     wrap="word")
        self.preview_txt.pack(fill="both", expand=True, padx=4, pady=(4,8))
        self.preview_txt.config(state="disabled")

        # Bind selection to update preview
        self.lb.bind("<<ListboxSelect>>", self._on_select)

        # Buttons
        btn_frame = tk.Frame(frame, bg=DARK_BG if self.theme_dark else None)
        btn_frame.pack(fill="x", pady=(4,0))
        tb.Button(btn_frame, text="OK", bootstyle="primary", command=self._on_ok).pack(side="left", padx=6)
        tb.Button(btn_frame, text="Close", bootstyle="secondary", command=self._on_close).pack(side="right", padx=6)

        # Modal wait
        self.wait_window(self)

    def _on_select(self, _evt=None):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        conv = self.conversations[idx]
        # Näytä preview
        self.preview_txt.config(state="normal")
        self.preview_txt.delete("1.0", "end")
        prompt = conv.get("prompt", "")
        response = conv.get("response", "")
        self.preview_txt.insert("end", f"User prompt:\n{prompt}\n\nAgent response:\n{response}")
        self.preview_txt.config(state="disabled")

    def _on_ok(self):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a conversation")
            return
        self.selected_conv = self.conversations[sel[0]]
        self.destroy()

    def _on_close(self):
        self.selected_conv = None
        self.destroy()

    def show(self):
        """Palauttaa valitun keskustelun dictin tai None."""
        return self.selected_conv
