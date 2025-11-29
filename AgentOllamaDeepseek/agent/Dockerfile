FROM python:3.11-slim

WORKDIR /app

# kopioi requirements ja asenna
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# kopioi agentin koodi
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]