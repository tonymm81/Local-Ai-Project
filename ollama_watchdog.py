# /usr/local/bin/ollama_watchdog.py
import time, datetime, sys, re, subprocess, json
import docker
import requests

CONTAINER = "ollama-debug"
MAX_SECONDS = 300
CPU_THRESHOLD = 85.0   # %
MEM_THRESHOLD_MB = 7000  # MB
CHECK_INTERVAL = 10
LOGFILE = "/var/log/ollama_watchdog.log"
WEBHOOK = None  # "https://hooks.example.com/..." tai None tän vois kattoo, saisko sen postaamaa ihan asiakas appii

client = docker.from_env()

def log(msg):
    line = f"{datetime.datetime.utcnow().isoformat()} {msg}"
    print(line)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")

def send_alert(msg):
    log("ALERT: " + msg)
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"text": msg}, timeout=5)
        except Exception as e:
            log(f"webhook error: {e}")

def get_last_created_time(container):
    try:
        logs = container.logs(tail=500).decode(errors="ignore").splitlines()
        # etsi viimeinen created_at JSON‑rivi
        for line in reversed(logs):
            if '"created_at"' in line:
                m = re.search(r'"created_at"\s*:\s*"([^"]+)"', line)
                if m:
                    return datetime.datetime.fromisoformat(m.group(1).replace("Z","+00:00"))
    except Exception as e:
        log(f"error reading logs: {e}")
    return None

def check_stats(container):
    try:
        stats = container.stats(stream=False)
        cpu_pct = calc_cpu_percent(stats)
        mem_bytes = stats["memory_stats"].get("usage",0)
        mem_mb = mem_bytes / (1024*1024)
        return cpu_pct, mem_mb
    except Exception as e:
        log(f"stats error: {e}")
        return 0.0, 0.0

def calc_cpu_percent(stats):
    try:
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        if system_delta > 0 and cpu_delta > 0:
            cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage",[])) or 1
            return (cpu_delta / system_delta) * cpu_count * 100.0
    except Exception:
        pass
    return 0.0

def main():
    while True:
        try:
            container = client.containers.get(CONTAINER)
        except docker.errors.NotFound:
            log(f"{CONTAINER} not found")
            time.sleep(CHECK_INTERVAL)
            continue

        last_created = get_last_created_time(container)
        if last_created:
            age = (datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - last_created).total_seconds()
            if age > MAX_SECONDS:
                send_alert(f"{CONTAINER} last created_at {age:.0f}s ago > {MAX_SECONDS}s. Stopping.")
                try:
                    container.stop(timeout=10)
                except Exception:
                    container.kill()
                time.sleep(5)
                continue

        cpu, mem = check_stats(container)
        if cpu > CPU_THRESHOLD or mem > MEM_THRESHOLD_MB:
            send_alert(f"{CONTAINER} high resource usage CPU={cpu:.1f}% MEM={mem:.0f}MB. Restarting.")
            try:
                container.restart(timeout=10)
            except Exception as e:
                log(f"restart failed: {e}")

        # lokianalyysi: etsi OOM/killed/error
        try:
            tail = container.logs(tail=200).decode(errors="ignore")
            if re.search(r'\b(oom|killed|out of memory|error|segfault|panic)\b', tail, re.I):
                send_alert(f"{CONTAINER} logs contain error keywords. Restarting.")
                container.restart(timeout=10)
        except Exception as e:
            log(f"log scan error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
