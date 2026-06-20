import tkinter as tk
from tkinter import filedialog, font
import requests
import threading
import traceback
import re
import json
from datetime import datetime
import os

PROXY_URL = "http://192.168.68.204:8080"  # säädä omaan proxyysi
API_URL = os.getenv("API_URL", "//192.168.68.204:5001/admin/reset") 
API_KEY = os.getenv("API_KEY", "") # tyhjä jos ei asetettu

# Värit ja fontit tummaan teemaan
BG = "#0f1115"
PANEL = "#121417"
CARD = "#1b1f24"
FG = "#e6eef6"
MUTED = "#9aa6b2"
ACCENT = "#4fb0ff"
FONT_FAMILY = "Segoe UI"  # vaihda tarvittaessa
FONT_SIZE = 11



def run_cancel():
# Hae avain: ympäristöstä ensisijaisesti, muuten UI:sta (jos lisäät kentän) 
    key = API_KEY or prompt_entry.get().strip() # käytä prompt_entryä fallbackina tai luo erillinen kenttä 
    if not key: 
        analytics_text.after(0, lambda: update_analytics_text("No API key set in environment or prompt entry.")) 
        return # Estä nappia painamasta useasti (UI feedback) 
    
    cancel_button.config(state="enabled") 
    analytics_text.after(0, lambda: update_analytics_text("Sending reset request..."))

def send_prompt():
    user_prompt = prompt_entry.get().strip()
    if not user_prompt:
        update_result("Please enter a prompt.")
        return

    payload = {
        "model": "pixtral-12b-q2:latest",
        "prompt": user_prompt,
        "max_tokens": 512,
        "temperature": 0.0
    }

    update_result("Waiting for response...")
    update_analytics_text("Fetching analytics...")

    def task():
        try:
            resp = requests.post(f"{PROXY_URL}/generate", json=payload, timeout=620)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text", "")
            result_text.after(0, lambda: update_result(text))

            req_id = data.get("request_id")
            if req_id:
                # Hae yksittäisen requestin analytiikkaa
                try:
                    stats_resp = requests.get(f"{PROXY_URL}/requests/{req_id}", timeout=10)
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

def upload_file():# thi has to plan. I dont know, if ollama takes files from requests. If not, then just unzip file content to prompt field
    filepath = filedialog.askopenfilename()
    if not filepath:
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # Liitetään tiedoston sisältö promptiin, voit muokata rajauksia
        preview = content[:2000]  # rajoita liikaa suurten tiedostojen estämiseksi
        prompt_entry.delete(0, tk.END)
        prompt_entry.insert(0, preview)
        update_analytics_text(f"Loaded file: {filepath.split('/')[-1]} (preview inserted into prompt)")
    except Exception as e:
        update_analytics_text(f"File read failed: {e}")

def format_text_for_display(text: str) -> str: 
    if not text: return "" 
    # 1) Yhdenmukaista välilyönnit 
    text = re.sub(r'\s+', ' ', text).strip() 
    # 2) Poista välilyönti ennen välimerkkejä (esim. "word , " -> "word,") 
    text = re.sub(r'\s+([,.;:!?])', r'\1', text) 
    # 3) Poista välilyönnit heti lainausmerkkien sisään ja ulkopuolelta # esim. ' " you " ' -> '"you"' 
    text = re.sub(r'\s*"\s*([^"]+?)\s*"\s*', r' "\1" ', text) 
    # 4) Lisää tyhjä rivi lauseiden jälkeen (. ! ? : ;) 
    text = re.sub(r'([.!?;:])\s+', r'\1\n\n', text) 
    # 5) Siisti mahdolliset moninkertaiset rivinvaihdot 
    text = re.sub(r'\n{3,}', '\n\n', text) 
    return text.strip()

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

def update_analytics_from_request(data):
    summary = data.get("summary", {})
    events = data.get("events", [])

    # Parsitaan eventit ja rakennetaan uudelleen koottu vastaus
    parsed_events = []
    reconstructed_parts = []
    for ev in events:
        ts = ev.get("ts")
        raw = ev.get("raw_line", "")
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"response": raw}

        # Etsi response-kenttä turvallisesti
        resp_fragment = ""
        if isinstance(parsed, dict):
            resp_fragment = parsed.get("response") or parsed.get("text") or ""
        else:
            resp_fragment = str(parsed)

        # Poista johtavat välilyönnit ja trimmaa
        resp_fragment = str(resp_fragment).lstrip()

        parsed_events.append({
            "ts": ts,
            "created_at": parsed.get("created_at") if isinstance(parsed, dict) else None,
            "response": resp_fragment,
            "done": parsed.get("done") if isinstance(parsed, dict) else None,
            "done_reason": parsed.get("done_reason") if isinstance(parsed, dict) else None,
            "raw": raw
        })

        if resp_fragment:
            reconstructed_parts.append(resp_fragment)

    # Yhdistä fragmentit välilyönnillä
    reconstructed_text = " ".join([p.strip() for p in reconstructed_parts if p.strip()])

    # Muodosta analytics-teksti
   # Yhdistä fragmentit välilyönnillä 
    reconstructed_text = " ".join([p.strip() for p in reconstructed_parts if p.strip()]) 
    # Jälkisiivous: poista välilyönnit ennen välimerkkejä ja siisti lainausmerkit 
    reconstructed_text = re.sub(r'\s+([,.;:!?])', r'\1', reconstructed_text) 
    reconstructed_text = re.sub(r'\s*"\s*([^"]+?)\s*"\s*', r'"\1"', reconstructed_text) 
    reconstructed_text = re.sub(r'\s+', ' ', reconstructed_text).strip() # Muotoile start_ts ja end_ts ihmislukuisiksi ja laske kesto 
    start_ts = summary.get('start_ts') 
    end_ts = summary.get('end_ts') 
    start_iso = None 
    end_iso = None 
    duration_s = None
    try: 
        if start_ts: 
            start_iso = datetime.fromtimestamp(float(start_ts)).isoformat(sep=' ') 
        if end_ts: 
            end_iso = datetime.fromtimestamp(float(end_ts)).isoformat(sep=' ') 
        if start_ts and end_ts: 
         duration_s = float(end_ts) - float(start_ts) 
    except Exception: 
        start_iso = start_iso or str(start_ts) 
        end_iso = end_iso or str(end_ts)
    

    header_lines = [ f"Request ID: {summary.get('request_id')}", 
                    f"Model: {summary.get('model')}", 
                    f"Latency ms: {summary.get('latency_ms')}", 
                    f"Tokens: {summary.get('tokens')}", 
                    f"Start: {start_iso or 'N/A'}", 
                    f"End: {end_iso or 'N/A'}"
                    , ] 
    if duration_s is not None: 
        header_lines.append(f"Duration: {duration_s:.2f} s")
    lines = header_lines + ["", "Events (last 10):"]
    # Lisää viimeiset 10 eventtiä siistissä muodossa
    for ev in parsed_events[-10:]:
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

    # Päivitä myös result_text uudelleen koottulla ja formatroidulla vastauksella
    if reconstructed_text:
        result_text.after(0, lambda: update_result(reconstructed_text))

# GUI setup
root = tk.Tk()
root.title("Agent Prompt App")
root.configure(bg=BG)

# Grid layout ja venytys
root.columnconfigure(0, weight=1)
root.rowconfigure(3, weight=1)
root.rowconfigure(4, weight=1)

# Fontit
base_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE)
bold_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE, weight="bold")

# Prompt label ja entry
lbl = tk.Label(root, text="Enter Prompt:", bg=BG, fg=MUTED, font=base_font)
lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(12,4))

prompt_entry = tk.Entry(root, bg=CARD, fg=FG, insertbackground=FG, font=base_font)
prompt_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,8))

# Buttons
button_frame = tk.Frame(root, bg=BG)
button_frame.grid(row=2, column=0, sticky="w", padx=12, pady=(0,8))

send_button = tk.Button(button_frame, text="Send Prompt", command=send_prompt, bg=ACCENT, fg="#0b1220", font=bold_font, activebackground="#3aa0ff")
send_button.pack(side="left", padx=(0,8))

upload_button = tk.Button(button_frame, text="Upload File", command=upload_file, bg="gray25", fg=FG, font=base_font)
upload_button.pack(side="left")

# Result text
result_frame = tk.Frame(root, bg=PANEL)
result_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(8,6))
result_frame.columnconfigure(0, weight=1)
result_frame.rowconfigure(0, weight=1)

result_text = tk.Text(result_frame, wrap="word", bg="#0b0d10", fg=FG, insertbackground=FG, font=base_font, relief="flat")
result_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
result_text.config(state="disabled")

# Analytics text
analytics_frame = tk.Frame(root, bg=PANEL)
analytics_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0,12))
analytics_frame.columnconfigure(0, weight=1)
analytics_frame.rowconfigure(0, weight=1)

analytics_text = tk.Text(analytics_frame, wrap="word", bg="#0b0d10", fg=MUTED, insertbackground=FG, font=base_font, relief="flat")
analytics_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
analytics_text.config(state="disabled")

cancel_button = tk.Button(button_frame, text="Cancel / Run reset", command=lambda: run_cancel(), bg="#b03a3a", fg="#fff", font=base_font, activebackground="#d04a4a") 
cancel_button.pack(side="left", padx=(8,0))

# Aloitusviesti
update_result("Ready. Enter a prompt or upload a file.")
update_analytics_text("Analytics will appear here after a request completes.")

root.mainloop()
