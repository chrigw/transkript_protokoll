# 1. Wähle ein schlankes Python-Image
FROM python:3.10-slim

# 2. System-Dependencies installieren (hier FFmpeg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Arbeitsverzeichnis festlegen
WORKDIR /app

# 4. Nur Pip-Dependencies kopieren, um Caching zu nutzen
COPY requirements.txt .

# 5. Python-Dependencies installieren
RUN pip install --no-cache-dir -r requirements.txt

# 6. Restlichen Quellcode kopieren
COPY . .

# 7. Port freigeben (Flask läuft standardmäßig auf 5000)
EXPOSE 5000

# 8. Start-Befehl: starte deine Flask-App mit Gunicorn
CMD ["gunicorn", "flask_transkript_app:app", "--bind", "0.0.0.0:5000", "--workers", "3"]
