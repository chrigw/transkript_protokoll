# ---------- 1) Basis-Image ----------
FROM python:3.10-slim

# ---------- 2) System-Pakete installieren ----------
# - ffmpeg für die Transkription
# - evtl. git, falls du Pakete direkt von GitHub ziehst
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git && \
    rm -rf /var/lib/apt/lists/*

# ---------- 3) Arbeitsverzeichnis ----------
WORKDIR /app

# ---------- 4) Abhängigkeiten kopieren & installieren ----------
# Kopiere nur requirements.txt, damit dieser Layer gecacht wird, solange sich
# deine Python-Dependencies nicht ändern.
COPY requirements.txt .

# Pip ohne Cache, damit das Image klein bleibt
RUN pip install --no-cache-dir -r requirements.txt

# ---------- 5) Restlichen Code kopieren ----------
# Jetzt kommt dein gesamter Quellcode hinzu. Ändert sich hier etwas, wird
# nicht erneut 'pip install' ausgeführt.
COPY . .

# ---------- 6) Port freigeben ----------
EXPOSE 5000

# ---------- 7) Start-Befehl ----------
# # Gunicorn mit 3 Workern; passt die Zahl nach Bedarf an
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "flask_transkript_app:app", "--workers", "3"]
# bind an $PORT  
CMD ["sh","-c","exec gunicorn flask_transkript_app:app --bind 0.0.0.0:$PORT --workers 3"]
