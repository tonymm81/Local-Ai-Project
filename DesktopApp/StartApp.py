import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import json
import threading
import time
import textwrap
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from dialogs.agent_dialog import AgentDialog
from dialogs.analytics_view import AnalyticsView
from dialogs.conversation_list_dialog import ConversationListDialog
from dialogs.delete_dialog import DeleteDialog
from dialogs.history_dialog import HistoryDialog
from dialogs.new_or_old_dialog import NewOrOldDialog
import os


from api.client import ApiClient
from data.server_repo import ServerRepository
from current_agent_store import CurrentAgentStore

import requests
import threading

API_URL = os.getenv("API_URL", "http://192.168.68.204:5001/admin/reset")
API_KEY = os.getenv("API_KEY", "ThisIsThePassw0rd!") # tyhjä jos ei asetettu

api_client = ApiClient(timeout=15)
repo = ServerRepository(api_client)
current_store = CurrentAgentStore(repo)

AGENT_DEFAULT_MODEL = {
    "pixatrail": "pixtral-12b-q2:latest",
    "ollama-dev": "phi_2_gguf:latest",
    "ollama-qwen": "qwen2.5:7b"
}
# Dummy data
AGENTS = {
    "Agent Qwen": {
        "topics": {
            "Weather parsing": [
                {"prompt":"How to parse temp?", "response":"Use sensor X..."},
                {"prompt":"Fix MQTT reconnect", "response":"Add backoff..."}
            ],
            "Calibration": [
                {"prompt":"Calibrate sensor", "response":"Do step A..."}
            ]
        }
    },
    "Agent Dev": {
        "topics": {
            "Deploy": [
                {"prompt":"Deploy steps", "response":"Build, push..."}
            ]
        }
    },
    "Agent Pixatrail": {
            "topics": {
                "Deploy": [
                    {"prompt":"Deploy steps", "response":"Build, push..."}
                ]
            }
        }
}



DARK_BG = "#1e1e1e"
DARK_PANEL = "#2b2b2b"
DARK_FG = "#e6e6e6"
ACCENT = "#3a7bd5"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Agent App Prototype")
        self.agent = None
        self.topic = None
        self.current_response = ""
        # Repo ja store (yksi instanssi sovellukselle)
        api_client = ApiClient(timeout=620)
        self.repo = ServerRepository(api_client)
        self.current_store = CurrentAgentStore(self.repo)
        # UI rakentaminen pysyy samana
        self.build_main_ui()
        # Käynnistä agentin valinta kuten ennen
        self.show_agent_dialog_startup()

    def select_agent(self, agent_id: str):
        print("select_agent called with:", agent_id)
        self.clear_current_agent_data()
        try:
            agent_data = self.current_store.load_agent(agent_id)
            print("loaded agent_data topics:", agent_data.topics)
            self.agent = agent_id
            self.current_agent = agent_data
            self.update_main_title()
            self.refresh_topics_ui()
        except Exception as e:
            print("select_agent error:", e)
            messagebox.showerror("API error", f"Failed to load agent data: {e}")
            self.current_store.clear()
            self.agent = None
            self.current_agent = None

    def clear_current_agent_data(self):
        """Tyhjennä paikallinen cache ja päivitä UI:"""
        self.current_store.clear()
        self.agent = None
        self.current_agent = None
        # Esimerkki UI‑tyhjennyksestä (sovita omaan UI:hin)
        try:
            self.prompt_entry.delete(0, "end")
        except Exception:
            pass
        self.update_main_title()

    # Esimerkkimetodi joka päivittää otsikon; säilytä oma toteutuksesi
    def update_main_title(self):
        title = f"{self.current_agent.display_name if getattr(self,'current_agent',None) else 'No agent selected'}"
        # päivitä label tai window title
        self.root.title(f"AI Agent App Prototype - {title}")

    def refresh_topics_ui(self):
        # Päivitä topic‑listaus UI:ssa käyttäen self.current_store.get_topics()
        topics = self.current_store.get_topics()
        # esim. päivitä listbox: self.topics_listbox.delete(0, 'end'); for t in topics: insert...
        pass

    def build_main_ui(self):
        top_frame = tk.Frame(self.root, bg=DARK_BG)
        top_frame.pack(fill="x", padx=8, pady=6)

        self.title_label = tk.Label(top_frame, text="No conversation selected", font=("Arial", 14),
                                        bg=DARK_BG, fg=DARK_FG)
        self.title_label.pack(side="left", padx=6)

        btn_frame = tk.Frame(self.root, bg=DARK_BG)
        btn_frame.pack(fill="x", padx=8, pady=4)

            # Käytä tb.Button (ttkbootstrap) jotta nappi noudattaa teemaa
        tb.Button(btn_frame, text="Agent", bootstyle="secondary", command=self.open_agent_picker).pack(side="left")
        tb.Button(btn_frame, text="History", bootstyle="secondary", command=self.show_history).pack(side="left")
        tb.Button(btn_frame, text="Analytics", bootstyle="secondary", command=self.show_analytics).pack(side="left")
        tb.Button(btn_frame, text="Exit", bootstyle="danger", command=self.root.quit).pack(side="right")

            # Prompt input (tb.Entry tai ttk.Entry)
        self.prompt_entry = tb.Entry(self.root, bootstyle="dark")
        self.prompt_entry.pack(fill="x", padx=8, pady=6)
        self.prompt_entry.insert(0, "Write your prompt here...")

            # Code editor label
        code_label = tk.Label(self.root, text="Code block (optional)", bg=DARK_BG, fg=DARK_FG)
        code_label.pack(anchor="w", padx=8)

            # ScrolledText: aseta värit manuaalisesti
        self.code_text = scrolledtext.ScrolledText(self.root, height=8, bg=DARK_PANEL, fg=DARK_FG, insertbackground=DARK_FG)
        self.code_text.pack(fill="both", padx=8, pady=4, expand=False)

            # Buttons
        action_frame = tk.Frame(self.root, bg=DARK_BG)
        action_frame.pack(fill="x", padx=8, pady=4)
        tb.Button(action_frame, text="Send Prompt", bootstyle="success", command=self.send_prompt).pack(side="left")
        self.cancel_button = tb.Button(action_frame, text="Cancel", bootstyle="secondary", command=self.cancel_prompt)
        self.cancel_button.pack(side="left")
            # Response area
        resp_label = tk.Label(self.root, text="Agent response", bg=DARK_BG, fg=DARK_FG)
        resp_label.pack(anchor="w", padx=8)
        self.response_area = scrolledtext.ScrolledText(self.root, height=10, state="disabled",
                                                        bg=DARK_PANEL, fg=DARK_FG, insertbackground=DARK_FG)
        self.response_area.pack(fill="both", padx=8, pady=4, expand=True)

    # Dialog 1 / 2
    def show_agent_dialog_startup(self):
        # AgentDialogin tulee palauttaa agentin avain (esim. "ollama-qwen")
        from dialogs.agent_dialog import AgentDialog
        # Jos sinulla on lista avaimista, käytä sitä; muuten käytä repo.agent_keys tai kovakoodattua listaa
        agent_keys = getattr(self.repo, "agent_keys", None) or ["pixatrail", "ollama-dev", "ollama-qwen"]
        dlg = AgentDialog(self.root, agent_keys, initial=True)
        chosen = dlg.show()
        if chosen:
            # Lataa agentin data palvelimelta ja aseta cache
            self.select_agent(chosen)
            # Kun agentti valittu, kysy uusi vai vanha keskustelu
            self.show_new_or_old()
        else:
            # käyttäjä peruutti; ei tehdä mitään
            pass

# Muissa paikoissa (ei startup)
    def open_agent_picker(self):
        from dialogs.agent_dialog import AgentDialog
        agent_keys = getattr(self.repo, "agent_keys", None) or ["pixatrail", "ollama-dev", "ollama-qwen"]
        # Jos haluat näyttönimet, lähetä pareja: [(id, display_name), ...]
        agents_for_dialog = [(k, k) for k in agent_keys]  # tai käytä display_name jos saat sen repo:sta
        dlg = AgentDialog(self.root, agents_for_dialog, initial=False)
        chosen = dlg.show()
        if chosen:
            # tee täsmälleen sama flow kuin käynnistyksessä
            self.select_agent(chosen)
            self.show_new_or_old()

    def show_new_or_old(self):
        dlg = NewOrOldDialog(self.root, theme_dark=True)
        mode, topic = dlg.show()

        if mode == "new" and topic:
            self.topic = topic
            # Varmista että topic näkyy paikallisessa cache:ssa (store) — palvelin luo keskustelun generate-kutsussa
            # Lisätään topic paikalliseen listaan, jotta UI päivittyy
            if self.current_agent and topic not in (self.current_agent.topics or []):
                # päivitä paikallinen AgentData
                self.current_agent.topics = (self.current_agent.topics or []) + [topic]
            self.update_main_title()
        elif mode == "old":
            self.show_history()
        else:
            return

        
    def update_main_title(self):
        self.title_label.config(text=f"{self.agent} — {self.topic}")

    # Dialog 3 / 4 History
    def show_history(self):
        if not self.agent:
            messagebox.showinfo("Info", "Choose an agent first")
            return

        # Hae topics current_store:sta
        topics = self.current_store.get_topics()
        dlg = HistoryDialog(self.root, agent_name=self.agent, topics=topics, theme_dark=True)
        topic, action = dlg.show()

        if action == "open" and topic:
            self.show_conversation_list(topic)
        elif action == "delete" and topic:
            self.show_delete_dialog(topic)
        else:
            return

    def show_conversation_list(self, topic):
        if not self.agent:
            messagebox.showinfo("Info", "Choose an agent first")
            return

        try:
            raw = self.repo.get_messages(self.agent, topic)
            print("DEBUG: repo.get_messages raw:", raw)  # poista debug myöhemmin
        except Exception as e:
            messagebox.showerror("API error", f"Failed to fetch messages: {e}")
            return

        # Hae viestilista turvallisesti
        items = []
        if isinstance(raw, dict):
            if "messages" in raw and isinstance(raw["messages"], list):
                items = raw["messages"]
            elif "items" in raw and isinstance(raw["items"], list):
                items = raw["items"]
            else:
                # fallback: etsi ensimmäinen lista arvosta
                for v in raw.values():
                    if isinstance(v, list):
                        items = v
                        break
        elif isinstance(raw, list):
            items = raw

        # Muunna dialogin odottamaan muotoon: {"prompt":..., "response":...}
        convs = []
        for it in items:
            if not isinstance(it, dict):
                convs.append({"prompt": "", "response": str(it)})
                continue
            prompt = it.get("prompt_text") or it.get("user") or it.get("input") or it.get("message") or ""
            response = it.get("response_text") or it.get("assistant") or it.get("response") or it.get("text") or it.get("content") or ""
            # jos vain yksi kenttä löytyy, päättele rooli
            if not prompt and response and it.get("role","").lower().startswith("user"):
                prompt, response = response, ""
            convs.append({"prompt": prompt, "response": response})

        print("DEBUG convs:", convs)  # varmista mitä dialogille annetaan
        dlg = ConversationListDialog(self.root, agent_name=self.agent, topic=topic, conversations=convs, theme_dark=True)
        chosen = dlg.show()
        if chosen:
            self.topic = topic
            self.update_main_title()
            self.prompt_entry.delete(0, "end")
            self.prompt_entry.insert(0, chosen.get("response", ""))


    # Dialog 5 Delete
    def show_delete_dialog(self, topic):
        dlg = DeleteDialog(self.root, agent_name=self.agent, topic=topic, theme_dark=True)
        if not dlg.show():
            return

        try:
            ok = self.current_store.delete_conversation(topic)
        except Exception as e:
            messagebox.showerror("API error", f"Failed to delete: {e}")
            return

        if ok:
            messagebox.showinfo("Deleted", "Topic deleted")
            # päivitä paikallinen tila
            if getattr(self, "current_agent", None) and getattr(self.current_agent, "topics", None):
                self.current_agent.topics = [t for t in self.current_agent.topics if t != topic]
            self.current_store.messages_cache.pop(topic, None)
            # päivitä UI
            try:
                self.refresh_topics_ui()
                self.update_main_title()
            except Exception:
                # fallback: lataa agent uudelleen jos UI ei päivity
                try:
                    self.select_agent(self.agent)
                except Exception as e:
                    print("select_agent failed after delete:", e)



    # Dialog 6 Analytics
    def show_analytics(self):
        # Jos haluat näyttää dynaamisen analytiikan, anna teksti tähän
        analytics_text = "Analytics data (dummy)\n\nSentiment: Neutral\nTokens: 123\nConfidence: 0.87"
        AnalyticsView(self.root, analytics_text=analytics_text, theme_dark=True)

    # Send prompt (combine prompt + code into single prompt string)
    def send_prompt(self):
        if not self.agent or not self.topic:
            messagebox.showinfo("Info", "Select agent and topic first")
            return
        prompt = self.prompt_entry.get().strip()
        code = self.code_text.get("1.0", "end").rstrip()
        combined = prompt
        if code:
            combined += "\n\n```python\n" + code + "\n```"

        model = getattr(self.current_agent, "default_model", None) or AGENT_DEFAULT_MODEL.get(self.agent)
        if not model:
            messagebox.showerror("Error", "No model configured for this agent")
            return

        try:
            msg = self.current_store.save_prompt_to_server(self.topic, combined, model, user_id="tester")
            self._display_response(msg.response_text or str(msg))
        except Exception as e:
            messagebox.showerror("API error", f"Failed to send prompt: {e}")

    def _simulate_send(self, payload):
        # Show payload in console for debugging
        print("Payload to send:", json.dumps(payload))
        time.sleep(1.5)  # simulate network
        # Dummy response
        resp = "Agent reply to: " + (payload["prompt"][:120].replace("\n"," "))
        # Append to dummy history
        AGENTS[self.agent]["topics"].setdefault(self.topic, []).append({"prompt":payload["prompt"], "response":resp})
        # Update UI in main thread
        self.root.after(0, lambda: self._display_response(resp))

    def _display_response(self, resp):
        self.response_area.config(state="normal")
        self.response_area.insert("end", "\n\n" + resp + "\n")
        self.response_area.config(state="disabled")

    def cancel_prompt(self):
        """
        Aloittaa reset/administratiivisen pyynnön tai peruuttaa sen, riippuen tilasta.
        Ensimmäinen painallus aloittaa pyynnön; napin teksti vaihtuu Abortiksi.
        Toinen painallus peruuttaa pyynnön.
        """
        # Jos ei käynnissä olevaa pyyntöä, aloitetaan uusi
        if getattr(self, "_cancel_event", None) is None:
            key = API_KEY or self.prompt_entry.get().strip()
            if not key:
                self._append_response_text("No API key set.")
                return

            self._cancel_event = threading.Event()

            # Vaihda nappi peruutusmoodiin
            try:
                self.cancel_button.config(text="Abort", bootstyle="danger", command=self.cancel_reset_request, state="normal")
            except Exception:
                pass

            self._append_response_text("Sending reset request...")

            def do_request():
                session = requests.Session()
                try:
                    # Jos haluat sovelluksen odottavan pitkään, käytä isoa timeoutia tai poista timeout.
                    # Esimerkki: timeout=600 (10 min)
                    resp = session.post(API_URL, headers={"x-api-key": key}, timeout=600)
                    if self._cancel_event.is_set():
                        text = "Request canceled by user."
                    else:
                        text = f"Status: {resp.status_code}\nResponse: {resp.text}"
                except Exception as e:
                    if getattr(self, "_cancel_event", None) is not None and self._cancel_event.is_set():
                        text = "Request canceled."
                    else:
                        text = f"Request failed: {e}"
                finally:
                    try:
                        session.close()
                    except Exception:
                        pass
                    # Päivitä UI pääsäikeessä
                    self.response_area.after(0, lambda: self._append_response_text(text))
                    # Palauta nappi alkuperäiseen tilaan
                    def reset_button():
                        try:
                            self.cancel_button.config(text="Cancel", bootstyle="secondary", command=self.cancel_prompt, state="normal")
                        except Exception:
                            pass
                        self._cancel_event = None
                    self.response_area.after(0, reset_button)

            threading.Thread(target=do_request, daemon=True).start()

        else:
            # Jos pyyntö on käynnissä ja käyttäjä painaa samaa nappia, kutsutaan peruutusta
            self.cancel_reset_request()

    def _append_response_text(self, text: str):
        """Lisää tekstiä response_area:han turvallisesti pääsäikeessä."""
        try:
            self.response_area.config(state="normal")
            self.response_area.insert("end", "\n\n" + text + "\n")
            self.response_area.see("end")
            self.response_area.config(state="disabled")
        except Exception:
            # varmistus: jos response_area ei ole käytettävissä, tulosta konsoliin
            print(text)

        
    def cancel_reset_request(self):
        """Merkitse käynnissä oleva pyyntö peruutetuksi ja päivitä UI."""
        if getattr(self, "_cancel_event", None) is None:
            return
        self._cancel_event.set()
        self._append_response_text("Canceling...")
        try:
            # estä napin uudelleenpainallus
            self.cancel_button.config(state="disabled")
        except Exception:
            pass

if __name__ == "__main__":
    root = tb.Window(themename="darkly")  # valitse esim. "darkly", "cyborg"
    app = App(root)
    root.geometry("800x700")
    root.mainloop()
