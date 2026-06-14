#!/bin/bash

LOGFILE="/var/log/agent_reset.log"
TIMESTAMP=$(date --iso-8601=seconds)

echo "$TIMESTAMP RESET requested by $SUDO_USER or $USER" >> "$LOGFILE"

# Kaikki agentit ja daemonit jotka halutaan resetoida
AGENTS=(
  "ollama-qwen"
  "ollama-qwen-backend"
  "ollama-dev"
  "ollama"
  "localai-agent"
  "ollama-proxy"
)

echo "$TIMESTAMP Restarting all agents..." >> "$LOGFILE"

for AGENT in "${AGENTS[@]}"; do
    echo "$TIMESTAMP Restarting $AGENT" >> "$LOGFILE"
    docker restart "$AGENT" >> "$LOGFILE" 2>&1
done

sleep 5

echo "$TIMESTAMP Running healthchecks..." >> "$LOGFILE"

# Healthcheckit kaikille agenteille
curl -sS --max-time 5 http://127.0.0.1:11440/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-qwen" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11439/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-qwen-backend" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11437/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-dev" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11435/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:7860/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for localai-agent" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:8080/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-proxy" >> "$LOGFILE"

echo "$TIMESTAMP RESET finished" >> "$LOGFILE"
