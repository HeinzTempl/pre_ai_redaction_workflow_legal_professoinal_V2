import os
from docx_redactor import process_docx, process_docx_api
from pdf_redactor import redact_pdf, redact_pdf_api
from file_converter import convert_docx_to_pdf, convert_msg_to_pdf, convert_doc_to_docx

import warnings
warnings.simplefilter("ignore", category=DeprecationWarning)

def main():
    # 🟢 Abfrage: Soll die OpenAI API zur Schwärzung genutzt werden?
    use_api_initial = input("Möchten Sie die Dokumente direkt über die OpenAI API schwärzen? (j/n): ").strip().lower() == 'j'

    # 🟢 Ordner abfragen
    folder = input("Bitte geben Sie den Pfad zum Ordner ein, der verarbeitet werden soll:\n").strip()
    if not os.path.isdir(folder):
        print("❌ Der angegebene Pfad ist kein gültiger Ordner!")
        return

    # 🟢 Soll DOCX/MSG in PDFs umgewandelt werden?
    convert_to_pdf = input("Möchten Sie DOCX und MSG Dateien in PDF umwandeln? (j/n): ").strip().lower() == 'j'

    # 🔵 Erstelle Unterordner
    conv_folder = os.path.join(folder, "converted")
    redacted_folder = os.path.join(folder, "redacted")
    os.makedirs(conv_folder, exist_ok=True)
    os.makedirs(redacted_folder, exist_ok=True)

    pdf_files_to_process = []

    # 🟢 Wenn Umwandlung JA, dann erst DOCX/MSG zu PDFs umwandeln
    if convert_to_pdf:
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()
                if ext == ".docx":
                    output_pdf = os.path.join(conv_folder, filename + ".pdf")
                    print(f"🔄 Konvertiere DOCX → PDF: {full_path}")

                    convert_docx_to_pdf(full_path, output_pdf)  # 📌 Sicherstellen, dass es nicht hängt

                    if os.path.exists(output_pdf):
                        pdf_files_to_process.append(output_pdf)
                    else:
                        print(f"⚠️ Konvertierung fehlgeschlagen für: {full_path}")
                elif ext == ".msg":
                    output_pdf = os.path.join(conv_folder, filename + ".pdf")
                    print(f"🔄 Konvertiere MSG → PDF: {full_path}")
                    convert_msg_to_pdf(full_path, output_pdf)
                    if os.path.exists(output_pdf):
                        pdf_files_to_process.append(output_pdf)
                elif ext == ".doc":  # NEU: Falls eine DOC-Datei vorhanden ist
                    docx_path = os.path.join(conv_folder, filename + ".docx")
                    print(f"🔄 Konvertiere DOC → DOCX: {full_path}")
                    convert_doc_to_docx(full_path, docx_path)
                    if os.path.exists(docx_path):
                        output_pdf = os.path.join(conv_folder, filename + ".pdf")
                        print(f"🔄 Konvertiere DOCX → PDF: {docx_path}")
                        convert_docx_to_pdf(docx_path, output_pdf)
                        if os.path.exists(output_pdf):
                            pdf_files_to_process.append(output_pdf)

        # Füge existierende PDFs zur Verarbeitungsliste hinzu
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path) and file.lower().endswith(".pdf"):
                pdf_files_to_process.append(full_path)

    else:
        # ❗❗ NEU: Falls KEINE Umwandlung, dann DOCX/DOC-Dokumente trotzdem verarbeiten!
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()

                if ext == ".pdf":
                    pdf_files_to_process.append(full_path)

                elif ext == ".docx":  # Falls keine PDF-Umwandlung, DOCX trotzdem verarbeiten!
                    output_docx = os.path.join(redacted_folder, file)
                    print(f"✏️ Verarbeite DOCX: {full_path}")
                    if use_api_initial:
                        process_docx_api(full_path, output_docx)
                    else:
                        process_docx(full_path, output_docx)

                elif ext == ".doc":  # Falls eine DOC-Datei vorhanden ist
                    docx_path = os.path.join(conv_folder, filename + ".docx")
                    print(f"🔄 Konvertiere DOC → DOCX: {full_path}")
                    convert_doc_to_docx(full_path, docx_path)
                    if os.path.exists(docx_path):
                        output_docx = os.path.join(redacted_folder, filename + ".docx")
                        print(f"✏️ Verarbeite DOCX: {docx_path}")
                        if use_api_initial:
                            process_docx_api(docx_path, output_docx)
                        else:
                            process_docx(docx_path, output_docx)

                elif ext == ".msg":
                    output_pdf = os.path.join(conv_folder, filename + ".pdf")
                    print(f"🔄 Konvertiere MSG → PDF (weil MSG nicht direkt geschwärzt werden kann): {full_path}")
                    convert_msg_to_pdf(full_path, output_pdf)
                    if os.path.exists(output_pdf):
                        pdf_files_to_process.append(output_pdf)

    # 🔵 Verarbeitung der PDFs
    for pdf_file in pdf_files_to_process:
        base = os.path.basename(pdf_file)
        output_file = os.path.join(redacted_folder, base)
        if os.path.exists(pdf_file):
            print(f"✏️ Verarbeite PDF: {pdf_file}")
            redact_pdf(pdf_file, output_file)

    # 🟢 Finale Abfrage: Sollen die geschwärzten Dateien durch OpenAI weiter verarbeitet werden?
    use_api_final = input("Möchten Sie die bereits geschwärzten Dokumente zusätzlich über die OpenAI API verarbeiten? (j/n): ").strip().lower() == 'j'

    if use_api_final:
        for file in os.listdir(redacted_folder):
            full_path = os.path.join(redacted_folder, file)
            if os.path.isfile(full_path):
                filename, ext = os.path.splitext(file)
                ext = ext.lower()
                if ext == ".docx":
                    output_docx_api = os.path.join(redacted_folder, f"{filename}_api.docx")
                    print(f"🔄 Schwärze DOCX weiter mit OpenAI API: {full_path}")
                    process_docx_api(full_path, output_docx_api)
                elif ext == ".pdf":
                    output_pdf_api = os.path.join(redacted_folder, f"{filename}_api.pdf")
                    print(f"🔄 Schwärze PDF weiter mit OpenAI API: {full_path}")
                    redact_pdf_api(full_path, output_pdf_api)

    print("✅ Verarbeitung abgeschlossen!")
    print(f"📁 Die redacted Dateien befinden sich im Unterordner 'redacted'.")

if __name__ == '__main__':
    main()