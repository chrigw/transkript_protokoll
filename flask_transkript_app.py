# flask_transkript_app.py

from flask import Flask, request, render_template, send_file, url_for
import os
import subprocess
import sys
import glob
import uuid

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

@app.route("/", methods=["GET", "POST"])
def index():
    transcript      = None
    excerpt_pdf_url = None
    error           = None

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

            # Audiodatei in den Session-Input-Ordner speichern
            input_path = os.path.join(session_input, file.filename)
            file.save(input_path)

            # Environment für den Subprocess kopieren & anpassen
            env = os.environ.copy()
            # Prompt per ENV weitergeben
            if prompt:
                env["USER_PROMPT"] = prompt
            # OUTPUT_DIR für das Transkriptionsskript setzen
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

            # Logging für Debug
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
                    # Fallback: suche beliebige TXT-Datei mit Basisnamen
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

    return render_template(
        "index.html",
        transcript=transcript,
        excerpt_pdf_url=excerpt_pdf_url,
        error=error
    )

# Download-Route mit Session-ID
@app.route("/download/<session_id>/<filename>")
def download_file(session_id, filename):
    path = os.path.join(OUTPUT_DIR, session_id, filename)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
