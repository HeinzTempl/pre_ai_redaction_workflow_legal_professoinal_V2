# file_converter.py

import os
import unicodedata
import re
from docx2pdf import convert
from docx import Document
import subprocess

import warnings
warnings.simplefilter("ignore", category=DeprecationWarning)

def normalize_filename(filename):
    nfkd_form = unicodedata.normalize('NFKD', filename)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('ASCII')
    only_ascii = re.sub(r'\s+', '_', only_ascii)
    return only_ascii

def convert_docx_to_pdf(input_file, output_file):
    try:
        # Stelle sicher, dass LibreOffice gefunden wird
        libreoffice_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"  # macOS-Pfad
        if not os.path.exists(libreoffice_path):
            libreoffice_path = "soffice"  # Falls LibreOffice über PATH verfügbar ist

        print(f"🔄 Konvertiere mit LibreOffice: {input_file} → {output_file}")

        # Lege den Zielordner fest
        output_folder = os.path.dirname(output_file)

        # Starte LibreOffice headless-Modus zur Konvertierung mit explizitem `--outdir`
        result = subprocess.run([
            libreoffice_path, "--headless", "--convert-to", "pdf", "--outdir", output_folder, input_file
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Debugging-Ausgabe für Fehleranalyse
        print("📄 LibreOffice Output:", result.stdout.decode())

        if result.stderr:
            print("⚠️ LibreOffice Fehler:", result.stderr.decode())  # Nur anzeigen, wenn Fehler vorhanden sind

        # Überprüfe, ob die Datei tatsächlich im angegebenen Ordner existiert
        converted_pdf = os.path.join(output_folder, os.path.splitext(os.path.basename(input_file))[0] + ".pdf")

        if os.path.exists(converted_pdf):
            print(f"✅ DOCX erfolgreich in PDF umgewandelt: {converted_pdf}")
        else:
            print(f"❌ Konvertierung abgeschlossen, aber {converted_pdf} wurde nicht gefunden.")

    except subprocess.CalledProcessError as e:
        print(f"❌ LibreOffice Fehler: {e}")
    except Exception as e:
        print(f"❌ Fehler bei der Umwandlung von DOCX zu PDF: {e}")
def convert_msg_to_pdf(input_file, output_file):
    """
    Konvertiert eine MSG-Datei in eine PDF-Datei.
    Hier wird die Konvertierung mit extract_msg und ReportLab durchgeführt.
    """
    try:
        # Wir importieren hier lokal, damit diese Funktion unabhängig funktioniert.
        import extract_msg
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        msg = extract_msg.Message(input_file)
        msg_sender = msg.sender
        msg_date = msg.date
        msg_subject = msg.subject
        msg_body = msg.body

        c = canvas.Canvas(output_file, pagesize=letter)
        width, height = letter
        textobject = c.beginText(40, height - 40)
        lines = [
            f"Subject: {msg_subject}",
            f"From: {msg_sender}",
            f"Date: {msg_date}",
            "",
            msg_body
        ]
        for line in lines:
            for subline in line.split("\n"):
                textobject.textLine(subline)
        c.drawText(textobject)
        c.showPage()
        c.save()
        print(f"[MSG -> PDF] {input_file} konvertiert nach {output_file}")
    except Exception as e:
        print(f"Fehler beim Konvertieren von {input_file}: {e}")

def convert_doc_to_docx(input_doc, output_docx):
    try:
        subprocess.run(["unoconv", "-f", "docx", "-o", output_docx, input_doc], check=True)
        print(f"✅ DOC erfolgreich in DOCX umgewandelt: {output_docx}")
    except Exception as e:
        print(f"❌ Fehler bei der Umwandlung von DOC zu DOCX: {e}")