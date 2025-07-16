FROM python:3.10-slim

# System-Packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# nur requirements.txt kopieren
COPY requirements.txt .

# alle Python-Deps installieren (inkl. whisperx via Git-Link)
RUN pip install --no-cache-dir -r requirements.txt

# übrigen Code kopieren
COPY . .

EXPOSE 5000

# auf $PORT binden (Render setzt $PORT automatisch)
CMD ["sh","-c","exec gunicorn flask_transkript_app:app --bind 0.0.0.0:$PORT --workers 3"]
