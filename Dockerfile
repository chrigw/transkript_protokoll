FROM python:3.10-slim

# 1) System-Pakete installieren
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 2) Arbeitsverzeichnis setzen
WORKDIR /app

# 3) Python-Abhängigkeiten installieren
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4) Quellcode kopieren
COPY . .

# 5) Port-Umgebung für Render
ENV PORT 10000
EXPOSE 10000

# 6) Gunicorn starten – jetzt mit dem richtigen Modulnamen!
CMD ["sh", "-c", "exec gunicorn flask_transkript_app:app \
    --bind 0.0.0.0:$PORT \
    --worker-class gthread \
    --workers 1 \
    --threads 4 \
    --timeout 600 \
    --preload"]
