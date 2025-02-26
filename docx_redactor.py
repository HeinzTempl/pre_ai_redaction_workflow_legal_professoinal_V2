from docx import Document
import re
import spacy
from llm_api import redact_text_api

# Lade das spaCy-Modell (achte darauf, dass du das entsprechende deutsche Modell installiert hast)
nlp = spacy.load("de_core_news_sm")

def redact_regex(text):
    """Ersetzt E-Mail-Adressen und Telefonnummern per Regex."""
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[REDACTED]', text)
    text = re.sub(r'\b\+?\d[\d\s-]{7,}\d\b', '[REDACTED]', text)
    return text

def redact_spacy(text):
    """Erkennt Namen & Firmennamen und ersetzt sie durch Platzhalter."""
    doc = nlp(text)
    redacted = text
    person_mapping = {}
    firm_mapping = {}
    person_counter = 0
    firm_counter = 0
    for ent in doc.ents:
        if ent.label_ == "PER":
            if ent.text not in person_mapping:
                placeholder = f"Person {chr(65 + person_counter)}"
                person_mapping[ent.text] = placeholder
                person_counter += 1
            redacted = redacted.replace(ent.text, person_mapping[ent.text])
        elif ent.label_ == "ORG":
            if ent.text not in firm_mapping:
                placeholder = f"Firma {chr(65 + firm_counter)}"
                firm_mapping[ent.text] = placeholder
                firm_counter += 1
            redacted = redacted.replace(ent.text, firm_mapping[ent.text])
    return redacted

def process_tables(doc):
    """Schwärzt Text in Tabellen."""
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cell.text = redact_spacy(redact_regex(cell.text))

def process_headers_and_footers(doc):
    """Schwärzt Text in Kopf- und Fußzeilen."""
    for section in doc.sections:
        for para in section.header.paragraphs:
            para.text = redact_spacy(redact_regex(para.text))
        for para in section.footer.paragraphs:
            para.text = redact_spacy(redact_regex(para.text))

def process_footnotes(doc):
    """Schwärzt Text in Fußnoten."""
    if hasattr(doc, "footnotes"):
        for footnote in doc.footnotes.part.document.paragraphs:
            footnote.text = redact_spacy(redact_regex(footnote.text))

def process_docx(file_path, output_path):
    """Hauptfunktion zur Schwärzung von DOCX-Dateien."""
    doc = Document(file_path)

    # 1️⃣ Schwärzung im normalen Text
    for para in doc.paragraphs:
        para.text = redact_spacy(redact_regex(para.text))

    # 2️⃣ Schwärzung in Tabellen
    process_tables(doc)

    # 3️⃣ Schwärzung in Kopf- und Fußzeilen
    process_headers_and_footers(doc)

    # 4️⃣ Schwärzung in Fußnoten
    process_footnotes(doc)

    # Speichern des neuen Dokuments
    doc.save(output_path)
    print(f"✅ DOCX erfolgreich geschwärzt: {output_path}")

def process_docx_api(file_path, output_path):
    """
    Liest ein DOCX-Dokument, extrahiert den gesamten Text und schickt ihn an die API.
    Der von der API zurückgelieferte redigierte Text wird dann in einem neuen DOCX-Dokument gespeichert.
    """
    doc = Document(file_path)
    full_text = "\n".join([para.text for para in doc.paragraphs])

    redacted_full_text = redact_text_api(full_text)

    new_doc = Document()
    for line in redacted_full_text.split("\n"):
        new_doc.add_paragraph(line)
    new_doc.save(output_path)
    print(f"✅ API-basierte Redaktion abgeschlossen: {output_path}")

# Beispielhafter Aufruf:
if __name__ == '__main__':
    input_file = 'input.docx'
    output_file = 'output_redacted.docx'
    process_docx(input_file, output_file)