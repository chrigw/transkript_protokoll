# flask_transkript_app.py

from flask import Flask, request, render_template, send_file, url_for
import os
import subprocess
import sys
import glob

app = Flask(__name__)

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













# from flask import Flask, request, render_template, send_file, url_for
# import os
# import subprocess
# import sys
# import glob
#
# app = Flask(__name__)
#
# # Pfade konfigurieren
# BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
# INPUT_DIR   = os.path.join(BASE_DIR, "input_data")
# OUTPUT_DIR  = os.path.join(BASE_DIR, "output_data")
# SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")
#
# os.makedirs(INPUT_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     transcript      = None
#     excerpt_pdf_url = None
#     error           = None
#
#     if request.method == "POST":
#         file = request.files.get("audio_file")
#         if not file or not file.filename:
#             error = "Keine Datei ausgewählt."
#         else:
#             # Audiodatei speichern
#             input_path = os.path.join(INPUT_DIR, file.filename)
#             file.save(input_path)
#
#             # Transkriptionsskript aufrufen
#             proc = subprocess.run(
#                 [sys.executable, SCRIPT_PATH, input_path],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE
#             )
#
#             # Ausgaben dekodieren
#             stdout = proc.stdout.decode("utf-8", errors="replace")
#             stderr = proc.stderr.decode("utf-8", errors="replace")
#
#             # Konsolen-Log
#             print("=== Transkriptionsskript STDOUT ===")
#             print(stdout)
#             print("=== Transkriptionsskript STDERR ===")
#             print(stderr)
#             print("=== Return Code:", proc.returncode, "===\n")
#
#             if proc.returncode != 0:
#                 error = (
#                     "🚨 Fehler bei der Transkription!<br>"
#                     f"<pre>STDOUT:\n{stdout or '<leer>'}\nSTDERR:\n{stderr or '<leer>'}</pre>"
#                 )
#             else:
#                 # Transkript laden
#                 base     = os.path.splitext(file.filename)[0]
#                 txt_path = os.path.join(OUTPUT_DIR, f"{base}.txt")
#                 if os.path.exists(txt_path):
#                     with open(txt_path, "r", encoding="utf-8") as f:
#                         transcript = f.read()
#                 elif stdout.strip():
#                     transcript = stdout
#                 else:
#                     # Fallback: Suche nach .txt im output_data
#                     matches = glob.glob(os.path.join(OUTPUT_DIR, f"{base}*.txt"))
#                     if matches:
#                         with open(matches[0], "r", encoding="utf-8") as f:
#                             transcript = f.read()
#
#                 # Finde den Protokoll-Auszug-PDF
#                 pdf_matches = glob.glob(os.path.join(OUTPUT_DIR, "*auszug*.pdf"))
#                 if pdf_matches:
#                     latest_pdf = max(pdf_matches, key=os.path.getmtime)
#                     excerpt_pdf_url = url_for("download_file", filename=os.path.basename(latest_pdf))
#
#     return render_template(
#         "index.html",
#         transcript=transcript,
#         excerpt_pdf_url=excerpt_pdf_url,
#         error=error
#     )
#
# @app.route("/download/<filename>")
# def download_file(filename):
#     path = os.path.join(OUTPUT_DIR, filename)
#     return send_file(path, as_attachment=True)
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)

















# from flask import Flask, request, render_template, send_file
# import os
# import subprocess
# import sys
# import glob
#
# app = Flask(__name__)
#
# # Pfade konfigurieren
# BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
# INPUT_DIR   = os.path.join(BASE_DIR, "input_data")
# OUTPUT_DIR  = os.path.join(BASE_DIR, "output_data")
# SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")
#
# os.makedirs(INPUT_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     transcript = None
#     error      = None
#
#     if request.method == "POST":
#         file = request.files.get("audio_file", None)
#         if not file or file.filename == "":
#             error = "Keine Datei ausgewählt."
#         else:
#             # Audiodatei speichern
#             input_path = os.path.join(INPUT_DIR, file.filename)
#             file.save(input_path)
#
#             # Transkriptionsskript aufrufen, Rohbytes einfangen
#             proc = subprocess.run(
#                 [sys.executable, SCRIPT_PATH, input_path],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE
#             )
#
#             # Manuell dekodieren, ungültige Bytes ersetzen
#             stdout = proc.stdout.decode("utf-8", errors="replace")
#             stderr = proc.stderr.decode("utf-8", errors="replace")
#
#             # Konsolen-Log
#             print("=== Transkriptionsskript STDOUT ===")
#             print(stdout)
#             print("=== Transkriptionsskript STDERR ===")
#             print(stderr)
#             print("=== Return Code:", proc.returncode, "===\n")
#
#             if proc.returncode != 0:
#                 error = (
#                     "🚨 Transkriptionsfehler!\n\n"
#                     f"--- STDOUT ---\n{stdout or '<leer>'}\n"
#                     f"--- STDERR ---\n{stderr or '<leer>'}\n"
#                     f"Exit Code: {proc.returncode}"
#                 )
#             else:
#                 base     = os.path.splitext(file.filename)[0]
#                 expected = os.path.join(OUTPUT_DIR, f"{base}.txt")
#
#                 # 1) Primär: Standard-Datei-Pfad
#                 if os.path.exists(expected):
#                     with open(expected, "r", encoding="utf-8") as f:
#                         transcript = f.read()
#
#                 else:
#                     # 2) Fallback: stdout des Skripts verwenden, falls vorhanden
#                     if stdout.strip():
#                         transcript = stdout
#
#                     else:
#                         # 3) Fallback: Suche im output_data-Ordner nach allen .txt-Dateien, die mit base beginnen
#                         pattern = os.path.join(OUTPUT_DIR, f"{base}*.txt")
#                         matches = glob.glob(pattern)
#                         if matches:
#                             with open(matches[0], "r", encoding="utf-8") as f:
#                                 transcript = f.read()
#                         else:
#                             error = "⚠️ Transkript ausgeführt, aber keine Ausgabedatei gefunden und kein stdout vorhanden."
#
#     return render_template("index.html", transcript=transcript, error=error)
#
# @app.route("/download/<filename>")
# def download_file(filename):
#     path = os.path.join(OUTPUT_DIR, filename)
#     return send_file(path, as_attachment=True)
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)















# from flask import Flask, request, render_template, send_file
# import os
# import subprocess
# import sys
#
# app = Flask(__name__)
#
# # Pfade konfigurieren
# BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
# INPUT_DIR   = os.path.join(BASE_DIR, "input_data")
# OUTPUT_DIR  = os.path.join(BASE_DIR, "output_data")
# SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")
#
# os.makedirs(INPUT_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     transcript = None
#     error      = None
#
#     if request.method == "POST":
#         file = request.files.get("audio_file", None)
#         if not file or file.filename == "":
#             error = "Keine Datei ausgewählt."
#         else:
#             # Audiodatei speichern
#             input_path = os.path.join(INPUT_DIR, file.filename)
#             file.save(input_path)
#
#             # Transkriptionsskript aufrufen, Rohbytes einfangen
#             proc = subprocess.run(
#                 [sys.executable, SCRIPT_PATH, input_path],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE
#             )
#
#             # Manuell dekodieren, ungültige Bytes ersetzen
#             stdout = proc.stdout.decode("utf-8", errors="replace")
#             stderr = proc.stderr.decode("utf-8", errors="replace")
#
#             # Logging in der Konsole
#             print("=== Transkriptionsskript STDOUT ===")
#             print(stdout)
#             print("=== Transkriptionsskript STDERR ===")
#             print(stderr)
#             print("=== Return Code:", proc.returncode, "===\n")
#
#             if proc.returncode != 0:
#                 error = (
#                     "🚨 Transkriptionsfehler!\n\n"
#                     f"--- STDOUT ---\n{stdout or '<leer>'}\n"
#                     f"--- STDERR ---\n{stderr or '<leer>'}\n"
#                     f"Exit Code: {proc.returncode}"
#                 )
#             else:
#                 # Ausgabe-Datei einlesen
#                 base     = os.path.splitext(file.filename)[0]
#                 out_path = os.path.join(OUTPUT_DIR, f"{base}.txt")
#                 if os.path.exists(out_path):
#                     with open(out_path, "r", encoding="utf-8") as f:
#                         transcript = f.read()
#                 else:
#                     error = "⚠️ Transkript erfolgreich ausgeführt, aber keine Ausgabedatei gefunden."
#
#     return render_template("index.html", transcript=transcript, error=error)
#
# @app.route("/download/<filename>")
# def download_file(filename):
#     path = os.path.join(OUTPUT_DIR, filename)
#     return send_file(path, as_attachment=True)
#
# if __name__ == "__main__":
#     # Debug-Modus liefert Console-Logs live
#     app.run(host="0.0.0.0", port=5000, debug=True)















# from flask import Flask, request, render_template, send_file
# import os
# import subprocess
#
# app = Flask(__name__)
#
# # Pfade konfigurieren
# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# INPUT_DIR = os.path.join(BASE_DIR, "input_data")
# OUTPUT_DIR = os.path.join(BASE_DIR, "output_data")
# SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")
#
# os.makedirs(INPUT_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     transcript = None
#     error = None
#     if request.method == "POST":
#         if "audio_file" not in request.files:
#             error = "Keine Datei ausgewählt."
#         else:
#             file = request.files["audio_file"]
#             if file.filename == "":
#                 error = "Keine Datei ausgewählt."
#             else:
#                 # Audiodatei speichern
#                 input_path = os.path.join(INPUT_DIR, file.filename)
#                 file.save(input_path)
#                 # Transkription aufrufen und Ausgabe einfangen
#                 try:
#                     result = subprocess.run(
#                         ["python", SCRIPT_PATH, input_path],
#                         check=True,
#                         capture_output=True,
#                         text=True
#                     )
#                     # Optional: stdout für Debug
#                     # print("STDOUT:", result.stdout)
#                     base = os.path.splitext(file.filename)[0]
#                     out_path = os.path.join(OUTPUT_DIR, f"{base}.txt")
#                     if os.path.exists(out_path):
#                         with open(out_path, "r", encoding="utf-8") as f:
#                             transcript = f.read()
#                     else:
#                         error = "Transkript erfolgreich ausgeführt, aber keine Ausgabedatei gefunden."
#                 except subprocess.CalledProcessError as e:
#                     # Zeige stderr im Fehlerfall an
#                     stderr = e.stderr if e.stderr else str(e)
#                     error = f"Verarbeitungsfehler beim Transkriptionsskript:\n{stderr}"
#     return render_template("index.html", transcript=transcript, error=error)
#
# @app.route("/download/<filename>")
# def download_file(filename):
#     path = os.path.join(OUTPUT_DIR, filename)
#     return send_file(path, as_attachment=True)
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)





# from flask import Flask, request, render_template, send_file
# import os
# import shutil
# import subprocess
#
# app = Flask(__name__)
#
# # Pfade konfigurieren
# BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# INPUT_DIR = os.path.join(BASE_DIR, "input_data")
# OUTPUT_DIR = os.path.join(BASE_DIR, "output_data")
# SCRIPT_PATH = os.path.join(BASE_DIR, "trans_meeting.py")
#
# os.makedirs(INPUT_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     transcript = None
#     error = None
#     if request.method == "POST":
#         if "audio_file" not in request.files:
#             error = "Keine Datei ausgewählt."
#         else:
#             file = request.files["audio_file"]
#             if file.filename == "":
#                 error = "Keine Datei ausgewählt."
#             else:
#                 # Datei speichern
#                 input_path = os.path.join(INPUT_DIR, file.filename)
#                 file.save(input_path)
#                 # Transkription aufrufen
#                 try:
#                     subprocess.run(["python", SCRIPT_PATH, input_path], check=True)
#                     base = os.path.splitext(file.filename)[0]
#                     out_path = os.path.join(OUTPUT_DIR, f"{base}.txt")
#                     with open(out_path, "r", encoding="utf-8") as f:
#                         transcript = f.read()
#                 except subprocess.CalledProcessError as e:
#                     error = f"Verarbeitungsfehler: {e}"
#     return render_template("index.html", transcript=transcript, error=error)
#
# @app.route("/download/<filename>")
# def download_file(filename):
#     path = os.path.join(OUTPUT_DIR, filename)
#     return send_file(path, as_attachment=True)
#
# if __name__ == "__main__":
#     # 0.0.0.0 macht die App im lokalen Netzwerk erreichbar
#     app.run(host="0.0.0.0", port=5000, debug=True)
