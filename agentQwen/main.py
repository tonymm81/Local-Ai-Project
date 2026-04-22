import os

from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

# Malli ja Ollama host polut ympäristöstä
MODEL_PATH = os.environ.get("MODEL_PATH", "/root/.ollama/models/library/qwen2.5")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "0.0.0.0:11434")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/root/.ollama/ollama.db")

# Esimerkki: jos koodi tarvitsee tiedostonimen
def model_file_path(filename="model.gguf"):
    return os.path.join(MODEL_PATH, filename)