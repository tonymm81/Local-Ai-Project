#!/bin/bash
LOGFILE="/var/log/agent_reset.log"
TIMESTAMP=$(date --iso-8601=seconds)
echo "$TIMESTAMP RESET requested by $SUDO_USER or $USER" >> "$LOGFILE"

# Lista konteista tai compose‑palveluista jotka halutaan resetata
docker restart ollama localai-agent >> "$LOGFILE" 2>&1
# tai jos compose: docker compose -f /path/to/docker-compose.yml restart ollama_proxy localai-agent

# odota hetki ja tee healthcheckit
sleep 3
curl -sS --max-time 5 http://127.0.0.1:7860/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for 7860" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11435/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for 11435" >> "$LOGFILE"

echo "$TIMESTAMP RESET finished" >> "$LOGFILE"