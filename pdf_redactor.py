import fitz  # PyMuPDF
import re



def redact_pdf(file_path, output_path):
    """
    Liest eine PDF-Datei, sucht nach sensiblen Mustern und schwärzt die entsprechenden Bereiche.
    (Verwendet lokale Regex-Muster.)
    """
    doc = fitz.open(file_path)

    # Lokale Regex-Muster (ähnlich wie bei DOCX):
    patterns = [
         r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',  # E-Mail-Adressen
        r'\b\+?\d[\d\s-]{7,}\d\b',                              # Telefonnummern
        r'\b(?:Herr|Frau|Dr\.|Prof\.)\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?\b',  # Namen mit Titeln
        r'\b[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)+\b',     # Generische Namen (mindestens 2 Wörter)
        r'\b(?:[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\s+(?:Straße|Strasse|Weg|Gasse|Platz|Allee|Damm|Ring|Ufer)\s+\d+[a-zA-Z]?\b'  # Adressen
    ]

    for page in doc:
        redaction_areas = []
        page_text = page.get_text()
        for pattern in patterns:
            for match in re.finditer(pattern, page_text):
                matched_str = match.group()
                areas = page.search_for(matched_str)
                redaction_areas.extend(areas)
        for rect in redaction_areas:
            page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(output_path)
    print(f"PDF-Redaktion abgeschlossen: {output_path}")

import fitz  # PyMuPDF für PDF-Verarbeitung
from llm_api import redact_text_api  # OpenAI API für Schwärzung nutzen

def redact_pdf_api(input_pdf, output_pdf):
    """
    Verarbeitet ein PDF über die OpenAI API und wendet echte Schwärzung an.
    """
    try:
        doc = fitz.open(input_pdf)

        for page in doc:
            # Extrahiere den Originaltext
            text = page.get_text("text")

            # Sende den extrahierten Text an die API zur Schwärzung
            redacted_text = redact_text_api(text)

            # Ersetze den Originaltext mit der geschwärzten Version
            for text_instance in page.search_for(text):
                page.add_redact_annot(text_instance, fill=(0, 0, 0))  # Schwarze Rechtecke
                page.apply_redactions()

        # Speichere das geschwärzte PDF
        doc.save(output_pdf)
        print(f"✅ API-basierte PDF-Schwärzung abgeschlossen: {output_pdf}")

    except Exception as e:
        print(f"❌ Fehler bei der API-Schwärzung von {input_pdf}: {e}")