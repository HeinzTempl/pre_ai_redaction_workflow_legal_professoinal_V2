import fitz  # PyMuPDF
import re
from docx_redactor import (EntityMapper, ACTIVE_REGEX_PATTERNS,
                            extract_entities, is_whitelisted, _should_skip_entity,
                            _is_grundbuch_fraction, is_learned_never_redact,
                            get_learned_always_redact)
from llm_api import redact_text_api


def redact_pdf(file_path, output_path, mapper=None):
    """
    Liest eine PDF-Datei, erkennt sensible Daten per Regex UND NER (Flair/spaCy)
    und schwärzt die entsprechenden Bereiche.
    """
    if mapper is None:
        mapper = EntityMapper()

    doc = fitz.open(file_path)

    # Brüche im gesamten Dokument sammeln (für Schutz)
    fraction_pattern = re.compile(r'\d{1,6}\s*/\s*\d{1,6}')

    for page in doc:
        page_text = page.get_text()
        if not page_text or not page_text.strip():
            continue

        # Alle Bruch-Bestandteile auf dieser Seite sammeln
        protected_numbers = set()
        for frac_match in fraction_pattern.finditer(page_text):
            frac_text = frac_match.group()
            # Zähler und Nenner einzeln schützen
            parts = re.split(r'\s*/\s*', frac_text)
            for part in parts:
                part = part.strip()
                if part:
                    protected_numbers.add(part)

        redaction_areas = []

        # === 1. Regex-basierte Schwärzung ===
        for pattern, replacement in ACTIVE_REGEX_PATTERNS:
            for match in pattern.finditer(page_text):
                matched_str = match.group()
                # Grundbuch-Brüche (128/542) nicht schwärzen
                if _is_grundbuch_fraction(matched_str):
                    continue
                # Auch Teile von Brüchen schützen (Zähler/Nenner einzeln)
                if matched_str.strip() in protected_numbers:
                    continue
                areas = page.search_for(matched_str)
                redaction_areas.extend(areas)

        # === 2. NER-basierte Schwärzung (Flair oder spaCy) ===
        entities = extract_entities(page_text, mapper)
        for ent in entities:
            ent_text = ent["text"].strip()
            ent_label = ent["label"]
            score = ent["score"]

            # Gelernt: NIE schwärzen
            if is_learned_never_redact(ent_text):
                mapper.skipped_whitelist.append((ent_text, ent_label))
                continue
            if is_whitelisted(ent_text, ent_label):
                mapper.skipped_whitelist.append((ent_text, ent_label))
                continue
            # Juristische Personen bei konservativ nicht schwärzen
            if ent_label == "ORG" and mapper.sensitivity == "konservativ":
                mapper.skipped_org_juristic.append((ent_text, ent_label))
                continue
            if score < mapper.confidence_threshold:
                mapper.skipped_low_confidence.append((ent_text, ent_label, score))
                continue
            if _should_skip_entity(ent_text, ent_label):
                continue

            if len(ent_text) > 1:
                # Bruch-Bestandteile nicht schwärzen
                if ent_text in protected_numbers:
                    continue
                areas = page.search_for(ent_text)
                redaction_areas.extend(areas)

        # === 3. Titel + Name Muster (konservativ) ===
        title_pattern = re.compile(
            r'\b(?:Herr|Frau|Dr\.|Prof\.|Mag\.|RA|RAin)\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?\b'
        )
        for match in title_pattern.finditer(page_text):
            areas = page.search_for(match.group())
            redaction_areas.extend(areas)

        # === 4. Gelernte "immer schwärzen"-Begriffe ===
        always = get_learned_always_redact()
        for label, terms in always.items():
            for term in terms:
                if term in page_text:
                    areas = page.search_for(term)
                    redaction_areas.extend(areas)

        # Schwärzung anwenden
        for rect in redaction_areas:
            page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    doc.save(output_path)
    print(f"PDF-Redaktion abgeschlossen: {output_path}")
    return mapper


def redact_pdf_api(input_pdf, output_pdf):
    """
    Verarbeitet ein PDF über die OpenAI API und wendet echte Schwärzung an.
    """
    try:
        doc = fitz.open(input_pdf)

        for page in doc:
            text = page.get_text("text")
            if not text or not text.strip():
                continue

            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

            for paragraph in paragraphs:
                if len(paragraph) < 5:
                    continue

                redacted_paragraph = redact_text_api(paragraph)

                if redacted_paragraph != paragraph:
                    original_words = paragraph.split()
                    redacted_words = redacted_paragraph.split()

                    i = 0
                    while i < len(original_words):
                        if i < len(redacted_words) and '[REDACTED]' in redacted_words[i]:
                            redact_start = i
                            j = i + 1
                            while j < len(redacted_words) and '[REDACTED]' in redacted_words[j]:
                                j += 1
                            original_chunk = ' '.join(original_words[redact_start:redact_start + (j - i)])
                            if original_chunk:
                                areas = page.search_for(original_chunk)
                                for rect in areas:
                                    page.add_redact_annot(rect, fill=(0, 0, 0))
                            i = j
                        else:
                            i += 1

                    page.apply_redactions()

        doc.save(output_pdf)
        print(f"API-basierte PDF-Schwärzung abgeschlossen: {output_pdf}")

    except Exception as e:
        print(f"Fehler bei der API-Schwärzung von {input_pdf}: {e}")
