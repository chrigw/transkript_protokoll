# trans_meeting.py

import os
import sys
import glob
import shutil
import subprocess
import asyncio
from datetime import datetime

import torch
import whisperx
from whisperx.diarize import DiarizationPipeline
import edge_tts
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT

# .env-Datei laden (OPENAI_API_KEY, HUGGINGFACE_HUB_TOKEN)
load_dotenv()

# Gerät für WhisperX wählen
device = "cuda" if torch.cuda.is_available() else "cpu"

# HuggingFace Hub Token (um private/gated Pipelines laden zu können)
hf_token = (
    os.getenv("HUGGINGFACE_HUB_TOKEN")
    or os.getenv("HF_TOKEN")
    or os.getenv("HUGGINGFACE_TOKEN")
)
if not hf_token:
    print("⚠️ Kein HuggingFace-Token gesetzt. Diarization-Pipeline könnte nicht geladen werden.")

# PATH anpassen, damit ffmpeg & Co. gefunden werden
os.environ["PATH"] = os.path.abspath(".") + os.pathsep + os.environ.get("PATH", "")


def pruefe_ffmpeg():
    """Stellt sicher, dass ffmpeg installiert ist."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"✅ ffmpeg gefunden unter: {ffmpeg_path}")
        try:
            version = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
            print(f"📦 ffmpeg Version: {version}")
        except subprocess.CalledProcessError as e:
            print("⚠️ Fehler beim Abrufen der ffmpeg-Version:", e)
    else:
        print("❌ ffmpeg wurde nicht gefunden!")
        print("🔧 Bitte installiere ffmpeg und füge es zum Systempfad hinzu.")
        sys.exit(1)


async def erstelle_meeting_audio():
    """Erzeugt per TTS (edge_tts) ein Meeting-Audio, falls keines vorhanden."""
    # … unveränderte edge_tts-Implementierung …
    pass


def transkribiere_audio_mit_diarisation(audio_pfad, sprache="de"):
    """
    Transkribiert Audio mit WhisperX und führt anschließend Sprecher-Diarisation durch.
    """
    # Auf CPU: float32 statt float16, um Fehler zu vermeiden
    model = whisperx.load_model("small", device, compute_type="float32")
    result = model.transcribe(audio_pfad, batch_size=16, language=sprache)

    print("🔗 VAD-Segmente zuordnen…")
    # DiarizationPipeline benötigt zwingend model_name:
    diarization = DiarizationPipeline(
        model_name="pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
        device=device
    )  # :contentReference[oaicite:0]{index=0}

    # führt die Diarisation aus und erhält ein DataFrame mit Zeitfenstern + Speaker-Labels
    diarize_df = diarization(audio_pfad)

    # ordnet die Speaker-Labels den Whisper-Segmenten zu
    result = whisperx.assign_word_speakers(diarize_df, result)  # :contentReference[oaicite:1]{index=1}

    # zurück in eine einfache Liste für die weitere Verarbeitung
    output = []
    for seg in result["segments"]:
        start   = seg["start"]
        end     = seg["end"]
        speaker = seg.get("speaker", "Sprecher")
        text    = seg["text"]
        output.append((start, end, speaker, text))
    return output


def speichere_als_markdown(transkript_liste, ordner="output_data"):
    """Speichert das Roh-Transkript als Markdown-Datei."""
    os.makedirs(ordner, exist_ok=True)
    dateiname = f"protokoll_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    pfad = os.path.join(ordner, dateiname)
    with open(pfad, "w", encoding="utf-8") as f:
        for start, end, speaker, text in transkript_liste:
            f.write(f"- **{speaker}** [{start:.1f}s–{end:.1f}s]: {text.strip()}\n\n")
    print(f"💾 Markdown gespeichert: {pfad}")
    return pfad


def generiere_protokoll_auszug(transkript):
    """Erzeugt mithilfe von OpenAI einen strukturierten Protokoll-Auszug."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Umgebungsvariable OPENAI_API_KEY nicht gesetzt.")
        return "[FEHLER] Kein API-Key vorhanden."
    client = OpenAI(api_key=api_key)

    # Default-Prompt (inklusive Ausgabe des vollständigen Transkripts)
    default_prompt = f"""
Du bist ein KI-Protokoll-Assistent. Analysiere das folgende Meeting-Transkript und erstelle:
1. Eine Zusammenfassung der Hauptpunkte
2. Eine Liste der getroffenen Entscheidungen
3. Eine Liste aller To-Dos mit Namen (falls genannt)

Am Ende gib bitte zusätzlich das vollständige Transkript noch einmal aus.

Transkript:
{transkript}

Gib die Antwort im folgenden Format aus:

## Zusammenfassung
...

## Entscheidungen
- ...

## To-Dos
- [Name]: [Aufgabe]

## Vollständiges Transkript
{transkript}
"""

    # Prüfen, ob ein Nutzer-Prompt per ENV gesetzt wurde
    template = os.getenv("USER_PROMPT")
    if template:
        try:
            prompt = template.format(transkript=transkript)
        except Exception as e:
            print(f"⚠️ Fehler beim Anwenden des Nutzer-Prompts: {e}")
            prompt = default_prompt
    else:
        prompt = default_prompt

    # Anfrage an OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du bist ein deutscher Meeting-Assistent."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        print(f"⚠️ Fehler bei der Anfrage an OpenAI: {e}")
        return "[FEHLER] Zusammenfassung konnte nicht erstellt werden."


def speichere_auszug(text, ordner="output_data"):
    """Speichert den Protokoll-Auszug als Markdown-Datei."""
    os.makedirs(ordner, exist_ok=True)
    dateiname = f"protokoll_auszug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    pfad = os.path.join(ordner, dateiname)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"📄 Auszug gespeichert: {pfad}")
    return pfad


def konvertiere_letzte_markdown_zu_pdf():
    """Konvertiert die zuletzt erstellte Markdown-Datei zu PDF."""
    md_files = sorted(glob.glob("output_data/*.md"), key=os.path.getmtime, reverse=True)
    if not md_files:
        print("❌ Keine Markdown-Dateien gefunden.")
        return
    latest_md = md_files[0]
    pdf_path = latest_md.replace(".md", ".pdf")

    with open(latest_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Header', parent=styles['Heading2'], fontSize=13, spaceAfter=0.5*cm))
    styles.add(ParagraphStyle(name='Sprecher', parent=styles['Normal'], fontSize=11, spaceAfter=0.3*cm, alignment=TA_LEFT))

    story = []
    for line in md_content.splitlines():
        if not line.strip():
            story.append(Spacer(1, 0.2*cm))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles['Header']))
        else:
            story.append(Paragraph(line, styles['Sprecher']))

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    try:
        doc.build(story)
        print(f"📄 PDF exportiert: {pdf_path}")
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der PDF: {e}")


if __name__ == "__main__":
    # 1) ffmpeg prüfen
    pruefe_ffmpeg()

    # 2) Meeting-Audio erzeugen oder laden
    audio_pfad = os.path.join("input_data", "meeting_audio.mp3")
    if not os.path.exists(audio_pfad):
        audio_pfad = asyncio.run(erstelle_meeting_audio())

    # 3) Audio transkribieren
    transkript_liste = transkribiere_audio_mit_diarisation(audio_pfad)
    speicherpfad_md = speichere_als_markdown(transkript_liste)

    # 4) Roh-Transkript ausgeben
    print("\n📄 Transkript mit Sprechererkennung:\n")
    plain_text = "\n".join(
        f"[{start:.1f}s–{end:.1f}s] {speaker}: {text.strip()}"
        for start, end, speaker, text in transkript_liste
    )
    print(plain_text)

    # 5) Protokoll-Auszug generieren und speichern
    auszug = generiere_protokoll_auszug(plain_text)
    speicherpfad_auszug = speichere_auszug(auszug)

    # 6) PDF-Konvertierung
    konvertiere_letzte_markdown_zu_pdf()
