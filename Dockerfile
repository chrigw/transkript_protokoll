FROM python:3.10-slim

# 1) System-Packages installieren (inkl. git für Pip-Git-URLs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Python-Abhängigkeiten (cached as long as requirements.txt is unchanged)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Restlichen Code kopieren
COPY . .

# 4) Port (nur dokumentativ, Render nutzt $PORT)
# Exponiere den von Render vorgegebenen Port
# (Render setzt zur Laufzeit PORT=10000)
EXPOSE 10000

# 5) Start auf dem von Render vorgegebenen Port mit hohem Timeout (600 s)
CMD ["sh","-c","exec gunicorn flask_transkript_app:app \
  --bind 0.0.0.0:$PORT \
  --worker-class gthread \
  --workers 1 \
  --threads 4 \
  --timeout 600 \
  --preload"]
