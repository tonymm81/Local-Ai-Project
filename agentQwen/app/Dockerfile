# /data/ai-agent3/app/Dockerfile
FROM python:3.11-slim

# Peruspaketit + curl healthcheckiä varten
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopioi sovellus
COPY . /app

# Asenna riippuvuudet jos requirements.txt löytyy
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Ympäristömuuttujien oletukset
ENV DATABASE_PATH=/root/.ollama/ollama.db
ENV MODEL_PATH=/root/.ollama/models/library/qwen2.5
ENV OLLAMA_HOST=0.0.0.0:11434
ENV PYTHONUNBUFFERED=1

# Controllerin portti
EXPOSE 11436

# Käynnistys: uvicorn jos löytyy, muuten python main.py
CMD ["sh", "-c", "if python -c 'import importlib; importlib.import_module(\"uvicorn\")' 2>/dev/null; then uvicorn main:app --host 0.0.0.0 --port 11436; else python main.py; fi"]
