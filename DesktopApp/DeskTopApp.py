import tkinter as tk
import requests
import json
import threading

# Agent endpoint
API_URL = "http://192.168.68.126:8080/generate"

def send_prompt():
    user_prompt = prompt_entry.get()
    payload = {
        "model": "pixtral-12b-q2:latest",
        "prompt": user_prompt,
        "max_tokens": 16,
        "temperature": 0.0
    }

    # Show waiting message immediately
    result_text.delete("1.0", tk.END)
    result_text.insert(tk.END, "Waiting for response...")

    def task():
        try:
            response = requests.post(API_URL, json=payload, timeout=320)
            if response.status_code == 200:
                data = response.json()
                clean_text = data.get("text", "").strip()
                # Päivitä UI pääsäikeestä
                result_text.after(0, lambda: update_result(clean_text))
            else:
                result_text.after(0, lambda: update_result(f"Error {response.status_code}: {response.text}"))
        except Exception as e:
            result_text.after(0, lambda: update_result(f"Request failed: {e}"))

    threading.Thread(target=task, daemon=True).start()

def update_result(text):
    result_text.delete("1.0", tk.END)
    result_text.insert(tk.END, text)

# GUI setup
root = tk.Tk()
root.title("Agent Prompt App")

tk.Label(root, text="Enter Prompt:").pack(pady=5)
prompt_entry = tk.Entry(root, width=50)
prompt_entry.pack(pady=5)

send_button = tk.Button(root, text="Send Prompt", command=send_prompt)
send_button.pack(pady=5)

result_text = tk.Text(root, width=80, height=20)
result_text.pack(pady=10)

root.mainloop()
