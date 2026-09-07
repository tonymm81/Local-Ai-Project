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
import traceback

from Formatters.TextFormatter import format_for_ui

from api.client import ApiClient
from data.server_repo import ServerRepository
from current_agent_store import CurrentAgentStore

import requests
import threading
BASE_URL = "http://192.168.68.204:8080"

API_URL = os.getenv("API_URL", "http://192.168.68.204:5001/admin/reset")
#Shutdown_URL = os.getenv("Shutdown_URL", "http://192.168.68.204:5001/admin/ShutDown")
API_KEY = os.getenv("API_KEY", "ThisIsThePassw0rd!") # tyhjä jos ei asetettu

#api_client = ApiClient(timeout=15)
#repo = ServerRepository(api_client)
#current_store = CurrentAgentStore(repo)

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
        self.last_request_id = None
        self.current_response = ""
        # Repo ja store (yksi instanssi sovellukselle)
        api_client = ApiClient(timeout=620)
        self.repo = ServerRepository(api_client)
        self.current_store = CurrentAgentStore(self.repo)
        # UI rakentaminen pysyy samana
        self._restored_flag = False#version 112
        self._restored_conversation_id = None#version 112
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
            self.clear_prompt_text()#version 112 changes
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
        tb.Button(btn_frame, text="Shutdown Server", bootstyle="danger", command=self.send_shutdown_request).pack(side="right")#version 113
        tb.Button(btn_frame, text="Update & Upgrade", bootstyle="warning", command=self.send_update_upgrade_request).pack(side="right")#version 113

        # Prompt input (multiline, scrollable) version 112
        prompt_label = tk.Label(self.root, text="Prompt (you can write long text)", bg=DARK_BG, fg=DARK_FG)
        prompt_label.pack(anchor="w", padx=8)

        # Use ScrolledText so long prompts are visible and scrollable
        self.prompt_entry = scrolledtext.ScrolledText(self.root, height=4, bg=DARK_PANEL, fg=DARK_FG, insertbackground=DARK_FG, wrap="word")
        self.prompt_entry.pack(fill="both", padx=8, pady=6, expand=False)
        # Optional lightweight placeholder: insert initial text and tag it so user can clear if they focus
        self.prompt_entry.insert("1.0", "Write your prompt here...")
        #version 112 end here
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
        self.cancel_button = tb.Button(action_frame, text="Cancel", bootstyle="secondary", command=self.send_reset_request)
        self.cancel_button.pack(side="left")
        tb.Button(action_frame, text="Clear Response", bootstyle="warning", command=self.clear_response_area).pack(side="left")
            # Response area
        resp_label = tk.Label(self.root, text="Agent response", bg=DARK_BG, fg=DARK_FG)
        resp_label.pack(anchor="w", padx=8)
        self.response_area = scrolledtext.ScrolledText(self.root, height=10, state="disabled",
                                                        bg=DARK_PANEL, fg=DARK_FG, insertbackground=DARK_FG)
        self.response_area.pack(fill="both", padx=8, pady=4, expand=True)


    def get_prompt_text(self) -> str: # version 112
        """Return trimmed prompt text from the scrollable prompt widget."""
        try:
            return self.prompt_entry.get("1.0", "end").strip()
        except Exception:
            # fallback if widget type changes
            try:
                return self.prompt_entry.get().strip()
            except Exception:
                return ""

    def set_prompt_text(self, text: str):
        """Set prompt text (replace existing)."""
        try:
            self.prompt_entry.delete("1.0", "end")
            self.prompt_entry.insert("1.0", text)
        except Exception:
            try:
                self.prompt_entry.delete(0, "end")
                self.prompt_entry.insert(0, text)
            except Exception:
                pass

    def clear_prompt_text(self):
        """Clear prompt widget content."""
        try:
            self.prompt_entry.delete("1.0", "end")
        except Exception:
            try:
                self.prompt_entry.delete(0, "end")
            except Exception:
                pass
                # version 112
    def clear_response_area(self):
        self.response_area.config(state="normal")
        self.response_area.delete("1.0", "end")
        self.response_area.config(state="disabled")
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
        if chosen: #version 112
            self.topic = topic
            self.update_main_title()
            # Prefill prompt with a clear restored marker + previous agent answer.
            restored_text = chosen.get("response", "") or ""
            restored_text = format_for_ui(restored_text)
            marker = "[RESTORED: previous agent answer]\n\n"
            new_prompt_marker = "[USER NEW PROMPT BELOW]\n\n"
            try:
                # If prompt_entry is ScrolledText (multiline)
                self.prompt_entry.delete("1.0", "end")
                self.prompt_entry.insert("1.0", marker + restored_text + "\n\n" + new_prompt_marker)
            except Exception:
                # Fallback for single-line Entry
                try:
                    self.prompt_entry.delete(0, "end")
                    self.prompt_entry.insert(0, marker + restored_text)
                except Exception:
                    pass
            # Mark internal state so UI/logic can know this was a restored conversation
            self._restored_flag = True
            self._restored_conversation_id = chosen.get("conversation_id")



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
        if not self.last_request_id:
            AnalyticsView(self.root, analytics_text="No analytics available yet.")
            return

        stats = self.repo.api.get_stats()
        req = self.repo.api.get_request_details(self.last_request_id)

        text = []
        text.append("=== Global Stats ===")
        text.append(f"Total requests: {stats.get('total_requests')}")
        text.append(f"Avg latency: {stats.get('avg_latency_ms')} ms")
        text.append(f"Total tokens: {stats.get('total_tokens')}")
        text.append("")

        summary = req.get("summary", {})
        text.append("=== Last Request Summary ===")
        text.append(f"Request ID: {summary.get('request_id')}")
        text.append(f"Model: {summary.get('model')}")
        text.append(f"Latency: {summary.get('latency_ms')} ms")
        text.append(f"Tokens: {summary.get('tokens')}")
        text.append("")

        AnalyticsView(self.root, analytics_text="\n".join(text))

    # Send prompt (combine prompt + code into single prompt string)
    

    def send_prompt(self): # version 112
        if not self.agent or not self.topic:
            messagebox.showinfo("Info", "Select agent and topic first")
            return
        prompt = self.get_prompt_text()#version 112
        code = self.code_text.get("1.0", "end").rstrip()
        combined = prompt
        if code:
            combined += "\n\n```python\n" + code + "\n```"

        model = getattr(self.current_agent, "default_model", None) or AGENT_DEFAULT_MODEL.get(self.agent)
        if not model:
            messagebox.showerror("Error", "No model configured for this agent")
            return

        if getattr(self, "_generation_running", False):
            self._append_response_text("A request is already running. Press Cancel/Abort to stop it first.")
            return

        # Merkkaa että generointi alkaa
        self._generation_running = True
        # Käytetään erillistä eventia reset/abort -logiikkaan
        self._cancel_event = None

        # Vaihda nappi peruutusmoodiin — Cancel painaa nyt cancel_prompt
        try:
            self.cancel_button.config(text="Abort", bootstyle="danger", command=self.send_reset_request, state="normal")
        except Exception:
            pass

        self._append_response_text("Sending prompt...")

        def task():
            try:
                msg = self.current_store.save_prompt_to_server(self.topic, combined, model, user_id="tester")
                # Jos peruutus on asetettu resetin kautta, älä päivitä UI:ta
                if getattr(self, "_cancel_event", None) is not None and self._cancel_event.is_set():
                    print("send_prompt: request completed but was cancelled; ignoring result")
                    return

                # msg voi olla dict tai olio; etsitään järkevä teksti
                try:
                    if isinstance(msg, dict):
                        resp_text = msg.get("response_text") or msg.get("text") or msg.get("response") or msg.get("content") or str(msg)
                    else:
                        resp_text = getattr(msg, "response_text", None) or str(msg)
                except Exception:
                    resp_text = str(msg)

                # Päivitä UI pääsäikeessä
                self.response_area.after(0, lambda: self._display_response(resp_text))
                self.last_request_id = getattr(self.repo.api, "last_request_id", None)

            except Exception as e:
                import traceback
                traceback.print_exc()

                # Jos käyttäjä on peruutuspyynnön aikana, älä näytä virheilmoitusta
                if getattr(self, "_cancel_event", None) is not None and self._cancel_event.is_set():
                    self.response_area.after(0, lambda: self._append_response_text("Request was cancelled during reset."))
                    return

                # Muodosta virheteksti heti ja sido se callbackiin
                err_text = f"Failed to send prompt: {e}"
                try:
                    import functools
                    self.response_area.after(0, functools.partial(messagebox.showerror, "API error", err_text))
                except Exception:
                    self.response_area.after(0, lambda: messagebox.showerror("API error", err_text))

                # Lisää virhe myös response_area:han
                self.response_area.after(0, lambda: self._append_response_text(err_text))

            finally:
                # generointi päättynyt — nollaa tila ja palauta nappi
                def reset_ui_after_send():
                    try:
                        self.cancel_button.config(text="Cancel", bootstyle="secondary", command=self.cancel_prompt, state="normal")
                    except Exception:
                        pass
                    self._generation_running = False
                    self._cancel_event = None
                    # Clear restored marker state if present
                    self._restored_flag = False
                    self._restored_conversation_id = None

                self.response_area.after(0, reset_ui_after_send)
        threading.Thread(target=task, daemon=True).start()
       

    def _display_response(self, resp):
        formatted = format_for_ui(resp)
        self.response_area.config(state="normal")
        self.response_area.insert("end", "\n\n" + formatted + "\n")
        self.response_area.config(state="disabled")

    def cancel_prompt(self):
        """
        Säilytetään API: käyttäjä painaa Cancel/Abort -> aina send_reset_request.
        """
        # Jos reset on jo käynnissä, ilmoitetaan; muuten käynnistetään reset
        if getattr(self, "_cancel_event", None) is not None:
            self._append_response_text("Reset already in progress.")
            return
        self.send_reset_request()


    def send_reset_request(self, timeout: int = 60):
        """
        Lähettää reset POSTin API_URL:iin. Kutsutaan aina kun käyttäjä painaa Cancel/Abort.
        Ei yritetä peruuttaa tätä kutsua paikallisesti — se on "kovaresetti".
        """
        # Jos reset on jo käynnissä, ilmoitetaan ja ei käynnistetä uutta
        if getattr(self, "_cancel_event", None) is not None:
            self._append_response_text("Reset already in progress.")
            return

        # Merkitään reset käynnissä olevaksi
        self._cancel_event = threading.Event()

        # Vaihdetaan nappi visuaalisesti Abort-tilaan (komento peruuttaa resetin ei ole tarpeen)
        try:
            self.cancel_button.config(text="Abort", bootstyle="danger", command=self.send_reset_request, state="normal")
        except Exception:
            pass

        self._append_response_text("Sending reset request...")

        def _reset_worker():
            session = requests.Session()
            text = None
            try:
                key = API_KEY or self.get_prompt_text()
                resp = session.post(API_URL, headers={"x-api-key": key}, timeout=timeout)
                # Näytetään aina palvelimen vastaus (status + body) jotta käyttäjä näkee tuloksen
                text = f"Reset response: {resp.status_code} - {resp.text}"
            except Exception as e:
                # Jos jokin menee pieleen, näytetään virhe
                text = f"Reset request failed: {e}"
            finally:
                try:
                    session.close()
                except Exception:
                    pass
                # Päivitetään UI pääsäikeessä
                try:
                    self.response_area.after(0, lambda: self._append_response_text(text))
                except Exception:
                    print("Failed to append response text:", text)
                # Palautetaan nappi takaisin Cancel-tilaan
                def _reset_ui():
                    try:
                        self.cancel_button.config(text="Cancel", bootstyle="secondary", command=self.send_reset_request, state="normal")
                    except Exception:
                        pass
                    # Merkitään reset päättyneeksi
                    self._cancel_event = None
                try:
                    self.response_area.after(0, _reset_ui)
                except Exception:
                    _reset_ui()

        threading.Thread(target=_reset_worker, daemon=True).start()

    def send_shutdown_request(self):#version 113
        try:
            key = API_KEY or self.get_prompt_text()
            resp = requests.post("http://192.168.68.204:5001/admin/ShutDown", headers={"x-api-key": key}, timeout=30)
            self._append_response_text(f"Shutdown response: {resp.status_code} - {resp.text}")
        except Exception as e:
            self._append_response_text(f"Shutdown failed: {e}")


    def send_update_upgrade_request(self):#version 113
        try:
            key = API_KEY or self.get_prompt_text()
            resp = requests.post("http://192.168.68.204:5001/admin/update_upgrade", headers={"x-api-key": key}, timeout=30)
            self._append_response_text(f"Update+Upgrade response: {resp.status_code} - {resp.text}")
        except Exception as e:
            self._append_response_text(f"Update+Upgrade failed: {e}")


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


if __name__ == "__main__":
    root = tb.Window(themename="darkly")  # valitse esim. "darkly", "cyborg"
    app = App(root)
    root.geometry("800x700")
    root.mainloop()
