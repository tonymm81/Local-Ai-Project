# DesktopApp.py
import tkinter as tk
from tkinter import filedialog, font
import requests
import threading
import traceback
import json
from datetime import datetime
import os

# Tuodaan formatointi ja analytics‑reconstruct funktiot erillisestä moduulista
from TextFormatter import format_text_for_display, reconstruct_from_events, preview_text, sanitize_conversation_title

PROXY = "http://192.168.68.204:8080"
API_URL = os.getenv("API_URL", "http://192.168.68.204:5001/admin/reset")
API_KEY = os.getenv("API_KEY", "ThisIsThePassw0rd!")

AGENT_DEFAULT_MODEL = {
    "pixatrail": "pixtral-12b-q2:latest",
    "ollama-dev": "phi_2_gguf:latest",
    "ollama-qwen": "qwen2.5:7b"
}
AGENTS = list(AGENT_DEFAULT_MODEL.keys())

# Värit ja fontit tummaan teemaan
BG = "#0f1115"
PANEL = "#121417"
CARD = "#1b1f24"
FG = "#e6eef6"
MUTED = "#9aa6b2"
ACCENT = "#4fb0ff"
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 11

def build_payload(selected_agent: str, selected_model: str | None, prompt: str):
    model = selected_model if selected_model else AGENT_DEFAULT_MODEL.get(selected_agent)
    if not model:
        raise ValueError(f"No model available for agent '{selected_agent}'")
    return {
        "agent": selected_agent,
        "model": model,
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.0
    }

def run_cancel():
    key = API_KEY or prompt_entry.get().strip()
    if not key:
        analytics_text.after(0, lambda: update_analytics_text("No API key set."))
        return

    cancel_button.config(state="disabled")
    analytics_text.after(0, lambda: update_analytics_text("Sending reset request..."))

    def do_request():
        try:
            resp = requests.post(
                API_URL,
                headers={"x-api-key": key},
                timeout=10
            )
            text = f"Status: {resp.status_code}\nResponse: {resp.text}"
        except Exception as e:
            text = f"Request failed: {e}"

        analytics_text.after(0, lambda: update_analytics_text(text))
        cancel_button.after(0, lambda: cancel_button.config(state="normal"))

    threading.Thread(target=do_request, daemon=True).start()

def send_prompt():
    user_prompt = prompt_entry.get().strip()
    agent = selected_agent.get() or "pixatrail"
    if not user_prompt:
        update_result("Please enter a prompt.")
        return

    selected_model = None

    try:
        payload = build_payload(agent, selected_model, user_prompt)
    except Exception as e:
        update_result(f"Payload build failed: {e}") 
        return

    update_result("Waiting for response...")
    update_analytics_text("Fetching analytics...")

    def task():
        try:
            print("OUTGOING PAYLOAD:", json.dumps(payload, ensure_ascii=False))
            resp = requests.post(f"{PROXY}/generate", json=payload, timeout=620)
            print("RESPONSE STATUS:", resp.status_code)
            print("RESPONSE BODY:", resp.text)
            if resp.status_code >= 400:
                result_text.after(0, lambda: update_result(f"Request failed: {resp.status_code}\n\n{resp.text}"))
                analytics_text.after(0, lambda: update_analytics_text("No analytics available (request failed)"))
                return

            data = resp.json()
            text = data.get("text", "")
            result_text.after(0, lambda: update_result(text))

            req_id = data.get("request_id")
            if req_id:
                try:
                    stats_resp = requests.get(f"{PROXY}/requests/{req_id}", timeout=10)
                    if stats_resp.status_code == 200:
                        stats_data = stats_resp.json()
                        analytics_text.after(0, lambda: update_analytics_from_request(stats_data))
                    else:
                        analytics_text.after(0, lambda: update_analytics_text(f"Stats fetch failed: {stats_resp.status_code}"))
                except Exception as e:
                    analytics_text.after(0, lambda: update_analytics_text(f"Stats request error: {e}"))
            else:
                analytics_text.after(0, lambda: update_analytics_text("No request_id returned"))
        except Exception as e:
            traceback.print_exc()
            result_text.after(0, lambda: update_result(f"Request failed: {e}"))
            analytics_text.after(0, lambda: update_analytics_text("No analytics available (request failed)"))

    threading.Thread(target=task, daemon=True).start()

def upload_file():
    filepath = filedialog.askopenfilename()
    if not filepath:
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        preview = content[:2000]
        prompt_entry.delete(0, tk.END)
        prompt_entry.insert(0, preview)
        update_analytics_text(f"Loaded file: {filepath.split('/')[-1]} (preview inserted into prompt)")
    except Exception as e:
        update_analytics_text(f"File read failed: {e}")

def update_analytics_from_request(data):
    summary = data.get("summary", {})
    events = data.get("events", [])
    reconstructed_text, analytics = reconstruct_from_events(events, summary, max_events=10)

    header_lines = [
        f"Request ID: {analytics.get('request_id')}",
        f"Model: {analytics.get('model')}",
        f"Latency ms: {analytics.get('latency_ms')}",
        f"Tokens: {analytics.get('tokens')}",
        f"Start: {analytics.get('start') or 'N/A'}",
        f"End: {analytics.get('end') or 'N/A'}"
    ]
    if analytics.get("duration_s") is not None:
        header_lines.append(f"Duration: {analytics['duration_s']:.2f} s")

    lines = header_lines + ["", "Events (last 10):"]
    for ev in analytics.get("events", []):
        ts_display = ""
        try:
            if ev["ts"]:
                ts_display = datetime.fromtimestamp(float(ev["ts"])).isoformat(sep=' ')
        except Exception:
            ts_display = str(ev["ts"])
        done_flag = ev.get("done")
        done_reason = ev.get("done_reason")
        resp = ev.get("response", "")
        resp_short = (resp[:200] + "...") if len(resp) > 200 else resp
        done_part = f"done={done_flag}" if done_flag is not None else "done=?"
        reason_part = f" ({done_reason})" if done_reason else ""
        lines.append(f"{ts_display}  | {done_part}{reason_part}  | {resp_short}")

    analytics_text.config(state="normal")
    analytics_text.delete("1.0", tk.END)
    analytics_text.insert(tk.END, "\n".join(lines))
    analytics_text.config(state="disabled")

    if reconstructed_text:
        result_text.after(0, lambda: update_result(reconstructed_text))

def update_result(text):
    formatted = format_text_for_display(text)
    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.insert(tk.END, formatted)
    result_text.config(state="disabled")

def update_analytics_text(text):
    analytics_text.config(state="normal")
    analytics_text.delete("1.0", tk.END)
    analytics_text.insert(tk.END, text)
    analytics_text.config(state="disabled")

# GUI setup
root = tk.Tk()
root.title("Agent Prompt App")
root.configure(bg=BG)

root.columnconfigure(0, weight=1)
root.rowconfigure(3, weight=1)
root.rowconfigure(4, weight=1)

selected_agent = tk.StringVar(master=root, value="pixatrail")

base_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE)
bold_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE, weight="bold")

lbl = tk.Label(root, text="Enter Prompt:", bg=BG, fg=MUTED, font=base_font)
lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(12,4))

prompt_entry = tk.Entry(root, bg=CARD, fg=FG, insertbackground=FG, font=base_font)
prompt_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,8))

button_frame = tk.Frame(root, bg=BG)
button_frame.grid(row=2, column=0, sticky="w", padx=12, pady=(0,8))

send_button = tk.Button(button_frame, text="Send Prompt", command=send_prompt, bg=ACCENT, fg="#0b1220", font=bold_font, activebackground="#3aa0ff")
send_button.pack(side="left", padx=(0,8))

upload_button = tk.Button(button_frame, text="Upload File", command=upload_file, bg="gray25", fg=FG, font=base_font)
upload_button.pack(side="left")

result_frame = tk.Frame(root, bg=PANEL)
result_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(8,6))
result_frame.columnconfigure(0, weight=1)
result_frame.rowconfigure(0, weight=1)

result_text = tk.Text(result_frame, wrap="word", bg="#0b0d10", fg=FG, insertbackground=FG, font=base_font, relief="flat")
result_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
result_text.config(state="disabled")

analytics_frame = tk.Frame(root, bg=PANEL)
analytics_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0,12))
analytics_frame.columnconfigure(0, weight=1)
analytics_frame.rowconfigure(0, weight=1)

analytics_text = tk.Text(analytics_frame, wrap="word", bg="#0b0d10", fg=MUTED, insertbackground=FG, font=base_font, relief="flat")
analytics_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
analytics_text.config(state="disabled")

cancel_button = tk.Button(button_frame, text="Cancel / Run reset", command=lambda: run_cancel(), bg="#b03a3a", fg="#fff", font=base_font, activebackground="#d04a4a")
cancel_button.pack(side="left", padx=(8,0))

tk.Label(button_frame, text="Agent:", bg=BG, fg=MUTED, font=base_font).pack(side="left", padx=(12,0))
for a in AGENTS:
    tk.Radiobutton(button_frame, text=a, variable=selected_agent, value=a,
                   bg=BG, fg=FG, selectcolor=PANEL, font=base_font).pack(side="left", padx=6)

update_result("Ready. Enter a prompt or upload a file.")
update_analytics_text("Analytics will appear here after a request completes.")

root.mainloop()
