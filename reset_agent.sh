#!/bin/bash
set -euo pipefail

LOGFILE="/var/log/agent_reset.log"
TIMESTAMP() { date --iso-8601=seconds; }

echo "$(TIMESTAMP) RESET requested by ${SUDO_USER:-$USER}" >> "$LOGFILE"

# Päivitä tarvittaessa nämä nimet vastaamaan `docker ps` outputtia
DOCKER_AGENTS=(
  "ollama-qwen"
  "ollama-qwen-backend"
  "ollama-dev-local"
  "ollama-local"
  "localai-agent"
)

SYSTEMD_SERVICES=(
  "ollama-proxy"
)

# Helper: get host port for a given container and container port (returns empty if not found)
get_host_port() {
  local container="$1"
  local container_port="$2"
  # docker port palauttaa esim "0.0.0.0:7861" tai tyhjän jos ei löydy
  docker port "$container" "$container_port" 2>/dev/null | sed -n 's/.*:\([0-9]*\)$/\1/p' || true
}

# Helper: wait for docker health status if available
wait_for_docker_health() {
  local container="$1"
  local timeout="${2:-30}"
  local start=$(date +%s)
  while true; do
    status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-health{{end}}' "$container" 2>/dev/null || echo "missing")
    if [ "$status" = "healthy" ]; then
      echo "$(TIMESTAMP) $container reported healthy" >> "$LOGFILE"
      return 0
    fi
    if [ "$status" = "no-health" ] || [ "$status" = "missing" ]; then
      echo "$(TIMESTAMP) $container has no Docker healthcheck" >> "$LOGFILE"
      return 1
    fi
    if [ $(( $(date +%s) - start )) -ge "$timeout" ]; then
      echo "$(TIMESTAMP) timeout waiting for $container health (status=$status)" >> "$LOGFILE"
      return 2
    fi
    sleep 1
  done
}

# Helper: http healthcheck to host port and path
http_healthcheck() {
  local name="$1"
  local host_port="$2"
  local path="$3"
  local tries=6
  local i=0
  while [ $i -lt $tries ]; do
    if curl -sS --max-time 5 "http://127.0.0.1:${host_port}${path}" >> "$LOGFILE" 2>&1; then
      echo "$(TIMESTAMP) HTTP health OK for $name on port $host_port$path" >> "$LOGFILE"
      return 0
    fi
    i=$((i+1))
    sleep 2
  done
  echo "$(TIMESTAMP) HTTP health FAILED for $name on port $host_port$path" >> "$LOGFILE"
  return 1
}

echo "$(TIMESTAMP) Restarting Docker agents..." >> "$LOGFILE"

for AGENT in "${DOCKER_AGENTS[@]}"; do
    echo "$(TIMESTAMP) Processing container: $AGENT" >> "$LOGFILE"
    if ! docker ps -a --format '{{.Names}}' | grep -xq "$AGENT"; then
        echo "$(TIMESTAMP) Container $AGENT not found, skipping" >> "$LOGFILE"
        continue
    fi

    echo "$(TIMESTAMP) Restarting Docker container: $AGENT" >> "$LOGFILE"
    if ! docker restart "$AGENT" >> "$LOGFILE" 2>&1; then
        echo "$(TIMESTAMP) ERROR restarting Docker container $AGENT" >> "$LOGFILE"
        continue
    fi

    # Odota ensin Dockerin healthcheck jos sellainen on
    wait_for_docker_health "$AGENT" 30
    rc=$?
    if [ $rc -eq 0 ]; then
        # healthy, jatketaan seuraavaan
        continue
    fi

    # Jos ei ole Docker healthcheck, yritä tehdä HTTP healthcheck host-porttiin
    # Tässä oletetaan yleisimmät container-portit; muokkaa tarvittaessa
    # Esim. ollama backendit expose 11434 container port, localai 7860 container port, uvicorn 8000
    case "$AGENT" in
      "ollama-qwen") container_port="11436"; path="/health" ;;
      "ollama-qwen-backend") container_port="11434"; path="/api/tags" ;;
      "ollama-dev-local") container_port="8000"; path="/api/tags" ;;
      "ollama-local") container_port="11434"; path="/api/tags" ;;
      "localai-agent") container_port="7860"; path="/health" ;;
      *) container_port="8000"; path="/" ;;
    esac

    host_port=$(get_host_port "$AGENT" "${container_port}/tcp")
    if [ -z "$host_port" ]; then
      echo "$(TIMESTAMP) Could not determine host port for $AGENT (container port $container_port), skipping HTTP healthcheck" >> "$LOGFILE"
      continue
    fi

    http_healthcheck "$AGENT" "$host_port" "$path"
done

echo "$(TIMESTAMP) Restarting systemd services..." >> "$LOGFILE"
for SERVICE in "${SYSTEMD_SERVICES[@]}"; do
    echo "$(TIMESTAMP) Restarting systemd service: $SERVICE" >> "$LOGFILE"
    if systemctl restart "$SERVICE" >> "$LOGFILE" 2>&1; then
        echo "$(TIMESTAMP) Restarted service $SERVICE" >> "$LOGFILE"
    else
        echo "$(TIMESTAMP) ERROR restarting systemd service $SERVICE" >> "$LOGFILE"
    fi
done

echo "$(TIMESTAMP) RESET finished" >> "$LOGFILE"
