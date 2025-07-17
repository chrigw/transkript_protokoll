# flask_transkript_app.py

from flask import Flask, request, render_template, send_file, url_for
import os
import subprocess
import sys
import glob

app = Flask(__name__)

# Health-Check-Route
@app.route("/health")
def health():
    return "OK", 200

# Pfade konfigurieren
BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
INPUT_DIR   = os.path.join(BASE_DIR, "input_data")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output_data")
SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")

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
            # Audiodatei speichern
            input_path = os.path.join(INPUT_DIR, file.filename)
            file.save(input_path)

            # Environment kopieren und ggf. USER_PROMPT setzen
            env = os.environ.copy()
            if prompt:
                env["USER_PROMPT"] = prompt

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

            # Logging
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
                # Transkript aus output_data laden
                base     = os.path.splitext(file.filename)[0]
                txt_path = os.path.join(OUTPUT_DIR, f"{base}.txt")
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        transcript = f.read()
                elif stdout.strip():
                    transcript = stdout
                else:
                    # Fallback: suche beliebige TXT-Datei mit Basisnamen
                    matches = glob.glob(os.path.join(OUTPUT_DIR, f"{base}*.txt"))
                    if matches:
                        with open(matches[0], "r", encoding="utf-8") as f:
                            transcript = f.read()

                # Protokoll-Auszug-PDF finden
                pdf_matches = glob.glob(os.path.join(OUTPUT_DIR, "*auszug*.pdf"))
                if pdf_matches:
                    latest_pdf = max(pdf_matches, key=os.path.getmtime)
                    excerpt_pdf_url = url_for("download_file", filename=os.path.basename(latest_pdf))

    return render_template(
        "index.html",
        transcript=transcript,
        excerpt_pdf_url=excerpt_pdf_url,
        error=error
    )

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
