import os
from docx_redactor import (process_docx, process_docx_api, EntityMapper,
                            set_sensitivity, set_ner_engine, get_engine_name,
                            redact_text_full)
from pdf_redactor import redact_pdf, redact_pdf_api
from file_converter import (convert_docx_to_pdf, convert_msg_to_pdf, convert_doc_to_docx,
                            extract_msg_text, convert_text_to_pdf)

import warnings
warnings.simplefilter("ignore", category=DeprecationWarning)

def main():
    print("=" * 60)
    print("  DSGVO-konforme Dokumenten-Schwärzung V2")
    print("=" * 60)

    # NER-Engine wählen
    print(f"\nAktive NER-Engine: {get_engine_name()}")
    engine_choice = input("NER-Engine wechseln? (1=Flair [genauer], 2=spaCy [schneller], Enter=beibehalten): ").strip()
    if engine_choice == "1":
        set_ner_engine("flair")
    elif engine_choice == "2":
        set_ner_engine("spacy")

    # Sensitivitätsstufe wählen
    print("\nSensitivitätsstufe wählen:")
    print("  1 = Konservativ (weniger schwärzen, weniger False Positives)")
    print("  2 = Standard    (ausgewogen)")
    print("  3 = Aggressiv   (mehr schwärzen, kann False Positives enthalten)")
    sensitivity_choice = input("Ihre Wahl (1/2/3) [Standard=2]: ").strip()

    sensitivity_map = {"1": "konservativ", "2": "standard", "3": "aggressiv"}
    sensitivity = sensitivity_map.get(sensitivity_choice, "standard")
    set_sensitivity(sensitivity)
    print(f"  -> Sensitivität: {sensitivity}")

    # API-Schwärzung?
    use_api_initial = input("\nDokumente direkt über die OpenAI API schwärzen? (j/n): ").strip().lower() == 'j'

    # Ordner
    folder = input("Pfad zum Ordner der verarbeitet werden soll:\n").strip()
    if not os.path.isdir(folder):
        print("Der angegebene Pfad ist kein gültiger Ordner!")
        return

    # Konvertierung?
    convert_to_pdf = input("DOCX und MSG Dateien in PDF umwandeln? (j/n): ").strip().lower() == 'j'

    # Unterordner
    conv_folder = os.path.join(folder, "converted")
    redacted_folder = os.path.join(folder, "redacted")
    os.makedirs(conv_folder, exist_ok=True)
    os.makedirs(redacted_folder, exist_ok=True)

    # EntityMapper
    mapper = EntityMapper(sensitivity=sensitivity)

    pdf_files_to_process = []

    if convert_to_pdf:
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()
                if ext == ".docx":
                    output_pdf = os.path.join(conv_folder, filename + ".pdf")
                    print(f"Konvertiere DOCX -> PDF: {full_path}")
                    convert_docx_to_pdf(full_path, output_pdf)
                    if os.path.exists(output_pdf):
                        pdf_files_to_process.append(output_pdf)
                    else:
                        print(f"Konvertierung fehlgeschlagen: {full_path}")
                elif ext == ".msg":
                    output_pdf = os.path.join(redacted_folder, filename + ".pdf")
                    print(f"Verarbeite MSG (Text -> Schwärzung -> PDF): {full_path}")
                    try:
                        msg_data = extract_msg_text(full_path)
                        # Text VOR der PDF-Erstellung schwärzen
                        redacted_lines = [
                            f"Betreff: {redact_text_full(msg_data['subject'], mapper)}",
                            f"Von: {redact_text_full(msg_data['sender'], mapper)}",
                            f"Datum: {msg_data['date']}",
                            "",
                            redact_text_full(msg_data["body"], mapper)
                        ]
                        convert_text_to_pdf(redacted_lines, output_pdf)
                        print(f"  MSG geschwärzt und als PDF gespeichert: {output_pdf}")
                    except Exception as e:
                        print(f"  Fehler bei MSG-Verarbeitung: {e}")
                elif ext == ".doc":
                    docx_path = os.path.join(conv_folder, filename + ".docx")
                    print(f"Konvertiere DOC -> DOCX: {full_path}")
                    convert_doc_to_docx(full_path, docx_path)
                    if os.path.exists(docx_path):
                        output_pdf = os.path.join(conv_folder, filename + ".pdf")
                        print(f"Konvertiere DOCX -> PDF: {docx_path}")
                        convert_docx_to_pdf(docx_path, output_pdf)
                        if os.path.exists(output_pdf):
                            pdf_files_to_process.append(output_pdf)

        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path) and file.lower().endswith(".pdf"):
                pdf_files_to_process.append(full_path)

    else:
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()

                if ext == ".pdf":
                    pdf_files_to_process.append(full_path)

                elif ext == ".docx":
                    output_docx = os.path.join(redacted_folder, file)
                    print(f"Verarbeite DOCX: {full_path}")
                    if use_api_initial:
                        process_docx_api(full_path, output_docx)
                    else:
                        mapper = process_docx(full_path, output_docx, mapper)

                elif ext == ".doc":
                    docx_path = os.path.join(conv_folder, filename + ".docx")
                    print(f"Konvertiere DOC -> DOCX: {full_path}")
                    convert_doc_to_docx(full_path, docx_path)
                    if os.path.exists(docx_path):
                        output_docx = os.path.join(redacted_folder, filename + ".docx")
                        print(f"Verarbeite DOCX: {docx_path}")
                        if use_api_initial:
                            process_docx_api(docx_path, output_docx)
                        else:
                            mapper = process_docx(docx_path, output_docx, mapper)

                elif ext == ".msg":
                    output_pdf = os.path.join(redacted_folder, filename + ".pdf")
                    print(f"Verarbeite MSG (Text -> Schwärzung -> PDF): {full_path}")
                    try:
                        msg_data = extract_msg_text(full_path)
                        # Text VOR der PDF-Erstellung schwärzen
                        redacted_lines = [
                            f"Betreff: {redact_text_full(msg_data['subject'], mapper)}",
                            f"Von: {redact_text_full(msg_data['sender'], mapper)}",
                            f"Datum: {msg_data['date']}",
                            "",
                            redact_text_full(msg_data["body"], mapper)
                        ]
                        convert_text_to_pdf(redacted_lines, output_pdf)
                        print(f"  MSG geschwärzt und als PDF gespeichert: {output_pdf}")
                    except Exception as e:
                        print(f"  Fehler bei MSG-Verarbeitung: {e}")

    # PDF-Verarbeitung
    for pdf_file in pdf_files_to_process:
        base = os.path.basename(pdf_file)
        output_file = os.path.join(redacted_folder, base)
        if os.path.exists(pdf_file):
            print(f"Verarbeite PDF: {pdf_file}")
            mapper = redact_pdf(pdf_file, output_file, mapper)

    # API-Nachbearbeitung
    use_api_final = input("\nGeschwärzte Dokumente zusätzlich über OpenAI API verarbeiten? (j/n): ").strip().lower() == 'j'

    if use_api_final:
        for file in os.listdir(redacted_folder):
            full_path = os.path.join(redacted_folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()
                if ext == ".docx":
                    output_docx_api = os.path.join(redacted_folder, f"{filename}_api.docx")
                    print(f"Schwärze DOCX weiter mit API: {full_path}")
                    process_docx_api(full_path, output_docx_api)
                elif ext == ".pdf":
                    output_pdf_api = os.path.join(redacted_folder, f"{filename}_api.pdf")
                    print(f"Schwärze PDF weiter mit API: {full_path}")
                    redact_pdf_api(full_path, output_pdf_api)

    # ==================== ZUSAMMENFASSUNG ====================
    print("\n" + "=" * 60)
    print(f"  Verarbeitung abgeschlossen!")
    print(f"  NER-Engine: {get_engine_name()}")
    print(f"  Sensitivität: {sensitivity}")
    print(f"  Dateien im Ordner: {redacted_folder}")
    print("=" * 60)

    total_entities = len(mapper.person_mapping) + len(mapper.org_mapping) + len(mapper.loc_mapping)
    if total_entities > 0:
        print(f"\n  Geschwärzte Entities ({total_entities} gesamt):")
        if mapper.person_mapping:
            print(f"    Personen ({len(mapper.person_mapping)}):")
            for original, placeholder in mapper.person_mapping.items():
                print(f"      {placeholder} = '{original}'")
        if mapper.org_mapping:
            print(f"    Firmen ({len(mapper.org_mapping)}):")
            for original, placeholder in mapper.org_mapping.items():
                print(f"      {placeholder} = '{original}'")
        if mapper.loc_mapping:
            print(f"    Orte ({len(mapper.loc_mapping)}):")
            for original, placeholder in mapper.loc_mapping.items():
                print(f"      {placeholder} = '{original}'")

    if mapper.skipped_whitelist:
        unique_skipped = set((t, l) for t, l in mapper.skipped_whitelist)
        print(f"\n  Nicht geschwärzt (Whitelist): {len(unique_skipped)} Begriffe")
        for text, label in sorted(unique_skipped):
            print(f"    [{label}] '{text}'")

    if mapper.skipped_org_juristic:
        unique_org = set((t, l) for t, l in mapper.skipped_org_juristic)
        print(f"\n  Nicht geschwärzt (Juristische Personen): {len(unique_org)} Begriffe")
        for text, label in sorted(unique_org):
            print(f"    '{text}'")

    if mapper.skipped_low_confidence:
        unique_skipped_lc = set((t, l) for t, l, c in mapper.skipped_low_confidence)
        print(f"\n  Nicht geschwärzt (zu geringe Confidence): {len(unique_skipped_lc)} Begriffe")
        for text, label in sorted(unique_skipped_lc):
            print(f"    [{label}] '{text}'")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
