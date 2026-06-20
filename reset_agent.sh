#!/bin/bash
set -euo pipefail

LOGFILE="/var/log/agent_reset.log"
TIMESTAMP=$(date --iso-8601=seconds)

echo "$TIMESTAMP RESET requested by $SUDO_USER or $USER" >> "$LOGFILE"

# Docker-kontit
DOCKER_AGENTS=(
  "ollama-qwen"
  "ollama-qwen-backend"
  "ollama-dev"
  "ollama"
  "localai-agent"
)

# Systemd-palvelut
SYSTEMD_SERVICES=(
  "ollama-proxy"
)

echo "$TIMESTAMP Restarting Docker agents..." >> "$LOGFILE"

for AGENT in "${DOCKER_AGENTS[@]}"; do
    echo "$TIMESTAMP Restarting Docker container: $AGENT" >> "$LOGFILE"
    docker restart "$AGENT" >> "$LOGFILE" 2>&1 || \
        echo "$TIMESTAMP ERROR restarting Docker container $AGENT" >> "$LOGFILE"
done

echo "$TIMESTAMP Restarting systemd services..." >> "$LOGFILE"

for SERVICE in "${SYSTEMD_SERVICES[@]}"; do
    echo "$TIMESTAMP Restarting systemd service: $SERVICE" >> "$LOGFILE"
    systemctl restart "$SERVICE" >> "$LOGFILE" 2>&1 || \
        echo "$TIMESTAMP ERROR restarting systemd service $SERVICE" >> "$LOGFILE"
done

sleep 5

echo "$TIMESTAMP Running healthchecks..." >> "$LOGFILE"

# Healthcheckit
curl -sS --max-time 5 http://127.0.0.1:11440/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-qwen" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11439/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-qwen-backend" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11437/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-dev" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:11435/api/tags >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:7860/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for localai-agent" >> "$LOGFILE"
curl -sS --max-time 5 http://127.0.0.1:8080/health >> "$LOGFILE" 2>&1 || echo "$TIMESTAMP healthcheck failed for ollama-proxy" >> "$LOGFILE"

echo "$TIMESTAMP RESET finished" >> "$LOGFILE"
