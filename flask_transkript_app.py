# flask_transkript_app.py

from flask import Flask, request, render_template, send_file, url_for
from dotenv import load_dotenv
import os
import subprocess
import sys
import glob
import uuid

# Env-Datei einlesen (SKIP_TRIMMING, USER_PROMPT, …)
load_dotenv()

app = Flask(__name__)

# Health-Check-Route
@app.route("/health")
def health():
    return "OK", 200

# Basis-Pfade
BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR   = os.path.join(BASE_DIR, "input_data")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output_data")
SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")

# Stelle sicher, dass Basis-Ordner existieren
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Optional: Audio-Trimming überspringen, wenn env var gesetzt ist
skip_trimming = os.getenv("SKIP_TRIMMING", "false").lower() in ("1", "true", "yes")
if skip_trimming:
    print("⚠️ SKIP_TRIMMING=true → Audio-Trimmen wird übersprungen.")

@app.route("/", methods=["GET", "POST"])
def index():
    transcript                 = None
    excerpt_pdf_url            = None
    transcript_download_url    = None
    transcript_filename        = None
    saved_folder               = None
    files                      = []
    error                      = None

    if request.method == "POST":
        file   = request.files.get("audio_file")
        prompt = request.form.get("prompt", "").strip()

        if not file or not file.filename:
            error = "Keine Datei ausgewählt."
        else:
            # Einmalige Session-ID erzeugen
            session_id = uuid.uuid4().hex

            # Session-spezifische Ordner anlegen
            session_input  = os.path.join(INPUT_DIR,  session_id)
            session_output = os.path.join(OUTPUT_DIR, session_id)
            os.makedirs(session_input,  exist_ok=True)
            os.makedirs(session_output, exist_ok=True)

            ############################################
            # Audiodatei in den Session-Input-Ordner speichern
            original_path = os.path.join(session_input, file.filename)
            file.save(original_path)
            
            # Standardmäßig arbeiten wir mit WAV (16 kHz, mono),
            # damit WhisperX das Audio zuverlässig laden kann
            base, _ = os.path.splitext(file.filename)
            if skip_trimming:
                # ganzer Clip → re-encode komplett
                converted_wav = os.path.join(session_input, f"{base}.wav")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", original_path,
                    "-ar", "16000",       # 16 kHz
                    "-ac", "1",           # Mono
                    "-c:a", "pcm_s16le",  # WAV-Codec
                    converted_wav
                ], check=True)
                input_path = converted_wav
            else:
                # nur erste 10 s → re-encode trimmed Segment
                trimmed_wav = os.path.join(session_input, f"trimmed_{base}.wav")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-ss", "0",
                    "-i", original_path,
                    "-t", "10",
                    "-ar", "16000",       # 16 kHz
                    "-ac", "1",           # Mono
                    "-c:a", "pcm_s16le",  # WAV-Codec
                    trimmed_wav
                ], check=True)
                input_path = trimmed_wav
            ############################################

            # Environment für den Subprocess kopieren & anpassen
            env = os.environ.copy()
            if prompt:
                env["USER_PROMPT"] = prompt
            env["OUTPUT_DIR"] = session_output

            # Transkriptionsskript aufrufen
            proc = subprocess.run(
                [sys.executable, SCRIPT_PATH, input_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )

            # Ausgaben dekodieren
            stdout = proc.stdout.decode("utf-8", errors="replace")
            stderr = proc.stderr.decode("utf-8", errors="replace")

            # Debug-Logging
            print("=== Transkriptionsskript STDOUT ===")
            print(stdout)
            print("=== Transkriptionsskript STDERR ===")
            print(stderr)
            print("=== Return Code:", proc.returncode, "===\n")

            if proc.returncode != 0:
                error = (
                    "🚨 Fehler bei der Transkription!<br>"
                    f"<pre>STDOUT:\n{stdout or '<leer>'}\nSTDERR:\n{stderr or '<leer>'}</pre>"
                )
            else:
                # 1) Transkript aus Session-Output laden
                base     = os.path.splitext(file.filename)[0]
                txt_path = os.path.join(session_output, f"{base}.txt")
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        transcript = f.read()
                elif stdout.strip():
                    transcript = stdout
                else:
                    # Fallback: suche beliebige TXT-Datei
                    matches = glob.glob(os.path.join(session_output, f"{base}*.txt"))
                    if matches:
                        with open(matches[0], "r", encoding="utf-8") as f:
                            transcript = f.read()

                # 2) Protokoll-Auszug-PDF finden
                pdf_matches = glob.glob(os.path.join(session_output, "*auszug*.pdf"))
                if pdf_matches:
                    latest_pdf = max(pdf_matches, key=os.path.getmtime)
                    excerpt_pdf_url = url_for(
                        "download_file",
                        session_id=session_id,
                        filename=os.path.basename(latest_pdf)
                    )

                # 3) Download-Link für Roh-Transkript
                if os.path.exists(txt_path):
                    transcript_filename     = os.path.basename(txt_path)
                    transcript_download_url = url_for(
                        "download_file",
                        session_id=session_id,
                        filename=transcript_filename
                    )

                # 4) Absoluter Pfad zum Session-Ordner
                saved_folder = session_output

                # 5) Alle Dateien im Session-Ordner als Download-Links
                if saved_folder and os.path.isdir(saved_folder):
                    for fname in sorted(os.listdir(saved_folder)):
                        url = url_for("download_file", session_id=session_id, filename=fname)
                        files.append({"name": fname, "url": url})

    return render_template(
        "index.html",
        transcript=transcript,
        excerpt_pdf_url=excerpt_pdf_url,
        transcript_download_url=transcript_download_url,
        transcript_filename=transcript_filename,
        saved_folder=saved_folder,
        files=files,
        error=error
    )

# Download-Route mit Session-ID
@app.route("/download/<session_id>/<filename>")
def download_file(session_id, filename):
    path = os.path.join(OUTPUT_DIR, session_id, filename)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
