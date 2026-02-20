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
def extract_msg_text(input_file):
    """
    Extrahiert den Text aus einer MSG-Datei und gibt ihn strukturiert zurück.
    Gibt ein Dict zurück: {"sender": ..., "date": ..., "subject": ..., "body": ...}
    """
    import extract_msg
    msg = extract_msg.Message(input_file)
    return {
        "sender": msg.sender or "",
        "date": str(msg.date or ""),
        "subject": msg.subject or "",
        "body": msg.body or "",
    }


def convert_text_to_pdf(text_lines, output_file):
    """
    Erzeugt eine saubere PDF aus einer Liste von Textzeilen.
    Unterstützt automatischen Seitenumbruch und UTF-8.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4
    margin_left = 50
    margin_top = 50
    margin_bottom = 50
    line_height = 14
    max_chars_per_line = 95  # Ungefähre Zeilenbreite

    # Versuche eine UTF-8-fähige Schrift zu laden
    font_name = "Helvetica"
    font_size = 10

    y = height - margin_top
    c.setFont(font_name, font_size)

    for line in text_lines:
        # Lange Zeilen umbrechen
        sublines = line.split("\n")
        for subline in sublines:
            # Manueller Zeilenumbruch bei langen Zeilen
            while len(subline) > max_chars_per_line:
                # Am letzten Leerzeichen vor dem Limit umbrechen
                break_pos = subline.rfind(" ", 0, max_chars_per_line)
                if break_pos == -1:
                    break_pos = max_chars_per_line
                chunk = subline[:break_pos]
                subline = subline[break_pos:].lstrip()

                if y < margin_bottom:
                    c.showPage()
                    c.setFont(font_name, font_size)
                    y = height - margin_top

                c.drawString(margin_left, y, chunk)
                y -= line_height

            # Restliche Zeile schreiben
            if y < margin_bottom:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - margin_top

            c.drawString(margin_left, y, subline)
            y -= line_height

    c.showPage()
    c.save()


def convert_msg_to_pdf(input_file, output_file):
    """
    Konvertiert eine MSG-Datei direkt in eine PDF-Datei (ohne Schwärzung).
    Wird nur noch als Fallback verwendet.
    """
    try:
        msg_data = extract_msg_text(input_file)
        lines = [
            f"Betreff: {msg_data['subject']}",
            f"Von: {msg_data['sender']}",
            f"Datum: {msg_data['date']}",
            "",
            msg_data["body"]
        ]
        convert_text_to_pdf(lines, output_file)
        print(f"[MSG -> PDF] {input_file} konvertiert nach {output_file}")
    except Exception as e:
        print(f"Fehler beim Konvertieren von {input_file}: {e}")

def convert_doc_to_docx(input_doc, output_docx):
    try:
        subprocess.run(["unoconv", "-f", "docx", "-o", output_docx, input_doc], check=True)
        print(f"✅ DOC erfolgreich in DOCX umgewandelt: {output_docx}")
    except Exception as e:
        print(f"❌ Fehler bei der Umwandlung von DOC zu DOCX: {e}")