"""
DSGVO-konforme Dokumenten-Schwärzung — Streamlit Web-Frontend
Starten mit: streamlit run app.py
"""

import streamlit as st
import os
import tempfile
import shutil
import zipfile
import io
import time
import warnings

warnings.simplefilter("ignore", category=DeprecationWarning)

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="DSGVO Dokumenten-Schwärzung",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== NER-MODELLE LADEN (einmalig, gecacht) ====================

@st.cache_resource(show_spinner="Lade NER-Modelle...")
def init_ner_models():
    """Lädt die NER-Modelle einmalig und gibt den Status zurück."""
    from docx_redactor import load_flair_models, load_spacy_model, get_engine_name
    try:
        load_flair_models()
        engine = "flair"
    except (ImportError, Exception):
        load_spacy_model()
        engine = "spacy"
    return engine, get_engine_name()


# Modelle beim Start laden
default_engine, default_engine_name = init_ner_models()


# ==================== SIDEBAR ====================

st.sidebar.title("Einstellungen")

# NER-Engine
engine_options = {"Flair (genauer)": "flair", "spaCy (schneller)": "spacy"}
selected_engine_label = st.sidebar.radio(
    "NER-Engine",
    list(engine_options.keys()),
    index=0 if default_engine == "flair" else 1,
    help="Flair: Zwei spezialisierte Modelle (legal + large), F1 ~92%. spaCy: Schneller, F1 ~85%."
)
selected_engine = engine_options[selected_engine_label]

# Sensitivität
sensitivity_options = {
    "Konservativ (weniger False Positives)": "konservativ",
    "Standard (ausgewogen)": "standard",
    "Aggressiv (mehr schwärzen)": "aggressiv",
}
selected_sensitivity_label = st.sidebar.radio(
    "Sensitivität",
    list(sensitivity_options.keys()),
    index=0,
    help="Konservativ: Threshold 0.90, nur sichere Treffer. Aggressiv: Threshold 0.60, schwärzt mehr."
)
selected_sensitivity = sensitivity_options[selected_sensitivity_label]

# Konvertierung
convert_to_pdf = st.sidebar.checkbox(
    "DOCX-Dateien in PDF konvertieren",
    value=False,
    help="Konvertiert DOCX via LibreOffice zu PDF und schwärzt dann die PDF. Benötigt LibreOffice."
)

# API-Nachbearbeitung
st.sidebar.markdown("---")
use_api = st.sidebar.checkbox(
    "OpenAI API Nachbearbeitung",
    value=False,
    help="Sendet geschwärzte Dokumente zusätzlich an die OpenAI API. ACHTUNG: Daten gehen extern!"
)
if use_api:
    st.sidebar.warning("Die Daten werden an OpenAI gesendet. Nur verwenden wenn der Text bereits vorgeschwärzt ist!")

# Info
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Aktive Engine:** {default_engine_name}  \n"
    f"**Alle Daten bleiben lokal** (außer bei API-Nutzung)"
)

# ==================== GELERNTE ENTITIES (Sidebar) ====================
from docx_redactor import (get_learned_data, add_never_redact, remove_never_redact,
                            add_always_redact, remove_always_redact)

learned = get_learned_data()
total_learned = len(learned.get("never_redact", [])) + sum(
    len(v) for v in learned.get("always_redact", {}).values()
)

if total_learned > 0:
    st.sidebar.markdown("---")
    with st.sidebar.expander(f"Gelernte Regeln ({total_learned})"):
        # Nie schwärzen
        if learned.get("never_redact"):
            st.markdown("**Nie schwärzen:**")
            for term in learned["never_redact"]:
                col_t, col_x = st.columns([4, 1])
                col_t.text(term)
                if col_x.button("X", key=f"rm_never_{term}"):
                    remove_never_redact(term)
                    st.rerun()

        # Immer schwärzen
        always = learned.get("always_redact", {})
        has_always = any(len(v) > 0 for v in always.values())
        if has_always:
            st.markdown("**Immer schwärzen:**")
            for label, terms in always.items():
                for term in terms:
                    col_t, col_x = st.columns([4, 1])
                    col_t.text(f"[{label}] {term}")
                    if col_x.button("X", key=f"rm_always_{label}_{term}"):
                        remove_always_redact(term, label)
                        st.rerun()


# ==================== HAUPTBEREICH ====================

st.title("DSGVO-konforme Dokumenten-Schwärzung")
st.markdown("Laden Sie Ihre Dokumente hoch — die Schwärzung erfolgt vollständig lokal auf Ihrem Rechner.")

# Upload-Key für Reset (ändert sich bei jedem Reset, erzwingt neuen Uploader)
if "upload_key" not in st.session_state:
    st.session_state["upload_key"] = 0

# Datei-Upload
uploaded_files = st.file_uploader(
    "Dokumente hochladen",
    type=["pdf", "docx", "doc", "msg"],
    accept_multiple_files=True,
    help="Unterstützte Formate: PDF, DOCX, DOC, MSG",
    key=f"file_uploader_{st.session_state['upload_key']}"
)

if uploaded_files:
    st.info(f"{len(uploaded_files)} Datei(en) hochgeladen: {', '.join(f.name for f in uploaded_files)}")


# ==================== VERARBEITUNG ====================

def process_files(uploaded_files, engine, sensitivity, convert_pdf, use_api_post):
    """Hauptverarbeitungsfunktion — verarbeitet alle hochgeladenen Dateien."""
    from docx_redactor import (
        process_docx, process_docx_api, EntityMapper,
        set_sensitivity, set_ner_engine, redact_text_full
    )
    from pdf_redactor import redact_pdf, redact_pdf_api
    from file_converter import (
        convert_docx_to_pdf, convert_doc_to_docx,
        extract_msg_text, convert_text_to_pdf
    )

    # Engine & Sensitivität setzen
    set_ner_engine(engine)
    set_sensitivity(sensitivity)

    # Temporäre Ordner
    work_dir = tempfile.mkdtemp()
    input_dir = os.path.join(work_dir, "input")
    conv_dir = os.path.join(work_dir, "converted")
    redacted_dir = os.path.join(work_dir, "redacted")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(conv_dir, exist_ok=True)
    os.makedirs(redacted_dir, exist_ok=True)

    # Dateien speichern
    for uf in uploaded_files:
        file_path = os.path.join(input_dir, uf.name)
        with open(file_path, "wb") as f:
            f.write(uf.getbuffer())

    mapper = EntityMapper(sensitivity=sensitivity)
    results = []
    pdf_files_to_process = []
    total_files = len(uploaded_files)
    progress_bar = st.progress(0, text="Starte Verarbeitung...")
    status_text = st.empty()
    current = 0

    # === Dateien verarbeiten ===
    for file in os.listdir(input_dir):
        full_path = os.path.join(input_dir, file)
        if not os.path.isfile(full_path):
            continue

        filename, ext = os.path.splitext(file)
        ext = ext.lower()
        current += 1
        progress_bar.progress(current / (total_files + 1), text=f"Verarbeite: {file}")

        if ext == ".docx":
            if convert_pdf:
                # DOCX -> PDF konvertieren, dann PDF schwärzen
                output_pdf = os.path.join(conv_dir, filename + ".pdf")
                status_text.text(f"Konvertiere {file} zu PDF...")
                convert_docx_to_pdf(full_path, output_pdf)
                if os.path.exists(output_pdf):
                    pdf_files_to_process.append((output_pdf, filename))
                else:
                    st.warning(f"Konvertierung fehlgeschlagen: {file}")
            else:
                # DOCX direkt schwärzen
                output_docx = os.path.join(redacted_dir, file)
                status_text.text(f"Schwärze {file}...")
                mapper = process_docx(full_path, output_docx, mapper)
                results.append({"name": file, "path": output_docx, "type": "docx"})

        elif ext == ".doc":
            # DOC -> DOCX -> weiterverarbeiten
            docx_path = os.path.join(conv_dir, filename + ".docx")
            status_text.text(f"Konvertiere {file} zu DOCX...")
            convert_doc_to_docx(full_path, docx_path)
            if os.path.exists(docx_path):
                if convert_pdf:
                    output_pdf = os.path.join(conv_dir, filename + ".pdf")
                    status_text.text(f"Konvertiere {filename}.docx zu PDF...")
                    convert_docx_to_pdf(docx_path, output_pdf)
                    if os.path.exists(output_pdf):
                        pdf_files_to_process.append((output_pdf, filename))
                else:
                    output_docx = os.path.join(redacted_dir, filename + ".docx")
                    status_text.text(f"Schwärze {filename}.docx...")
                    mapper = process_docx(docx_path, output_docx, mapper)
                    results.append({"name": filename + ".docx", "path": output_docx, "type": "docx"})
            else:
                st.warning(f"DOC-Konvertierung fehlgeschlagen: {file}")

        elif ext == ".msg":
            # MSG: Text extrahieren -> schwärzen -> PDF
            status_text.text(f"Schwärze E-Mail {file}...")
            try:
                msg_data = extract_msg_text(full_path)
                redacted_lines = [
                    f"Betreff: {redact_text_full(msg_data['subject'], mapper)}",
                    f"Von: {redact_text_full(msg_data['sender'], mapper)}",
                    f"Datum: {msg_data['date']}",
                    "",
                    redact_text_full(msg_data["body"], mapper)
                ]
                output_pdf = os.path.join(redacted_dir, filename + ".pdf")
                convert_text_to_pdf(redacted_lines, output_pdf)
                results.append({"name": filename + ".pdf", "path": output_pdf, "type": "pdf"})
            except Exception as e:
                st.warning(f"MSG-Verarbeitung fehlgeschlagen für {file}: {e}")

        elif ext == ".pdf":
            pdf_files_to_process.append((full_path, filename))

    # === PDF-Schwärzung ===
    for pdf_path, pdf_name in pdf_files_to_process:
        output_pdf = os.path.join(redacted_dir, pdf_name + ".pdf")
        status_text.text(f"Schwärze {pdf_name}.pdf...")
        mapper = redact_pdf(pdf_path, output_pdf, mapper)
        results.append({"name": pdf_name + ".pdf", "path": output_pdf, "type": "pdf"})

    # === Optional: API-Nachbearbeitung ===
    if use_api_post:
        status_text.text("API-Nachbearbeitung...")
        for res in results:
            if res["type"] == "docx":
                api_path = res["path"].replace(".docx", "_api.docx")
                process_docx_api(res["path"], api_path)
                res["path"] = api_path
                res["name"] = res["name"].replace(".docx", "_api.docx")
            elif res["type"] == "pdf":
                api_path = res["path"].replace(".pdf", "_api.pdf")
                redact_pdf_api(res["path"], api_path)
                res["path"] = api_path
                res["name"] = res["name"].replace(".pdf", "_api.pdf")

    progress_bar.progress(1.0, text="Fertig!")
    status_text.text("Verarbeitung abgeschlossen!")

    # Download-Daten vorbereiten (Dateien in Memory laden, damit temp-Ordner gelöscht werden kann)
    for res in results:
        with open(res["path"], "rb") as f:
            res["data"] = f.read()

    # Temp-Ordner aufräumen
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass

    return results, mapper


# ==================== START-BUTTON ====================

if uploaded_files:
    col1, col2 = st.columns([1, 4])
    with col1:
        start_button = st.button(
            "Schwärzung starten",
            type="primary",
            use_container_width=True
        )

    if start_button:
        st.markdown("---")

        with st.spinner("Verarbeitung läuft..."):
            results, mapper = process_files(
                uploaded_files, selected_engine, selected_sensitivity,
                convert_to_pdf, use_api
            )

        # Ergebnisse im Session-State speichern
        st.session_state["results"] = results
        st.session_state["mapper"] = mapper

    # Ergebnisse anzeigen (aus Session-State, überlebt Reruns)
    if "results" in st.session_state:
        results = st.session_state["results"]
        mapper = st.session_state["mapper"]

        if results:
            st.success(f"{len(results)} Datei(en) erfolgreich geschwärzt!")

            # Download-Bereich
            st.subheader("Geschwärzte Dateien herunterladen")

            # Einzelne Downloads
            download_cols = st.columns(min(len(results), 3))
            for i, res in enumerate(results):
                col = download_cols[i % 3]
                with col:
                    mime = "application/pdf" if res["type"] == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    st.download_button(
                        label=f"  {res['name']}",
                        data=res["data"],
                        file_name=res["name"],
                        mime=mime,
                        use_container_width=True
                    )

            # ZIP-Download bei mehreren Dateien
            if len(results) > 1:
                st.markdown("")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for res in results:
                        zf.writestr(res["name"], res["data"])
                zip_buffer.seek(0)
                st.download_button(
                    label="Alle Dateien als ZIP herunterladen",
                    data=zip_buffer,
                    file_name="redacted_documents.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            # ==================== ZUSAMMENFASSUNG ====================

            st.markdown("---")
            st.subheader("Zusammenfassung")

            total_entities = len(mapper.person_mapping) + len(mapper.org_mapping) + len(mapper.loc_mapping)

            # Metriken
            met_cols = st.columns(4)
            met_cols[0].metric("Dateien verarbeitet", len(results))
            met_cols[1].metric("Personen erkannt", len(mapper.person_mapping))
            met_cols[2].metric("Firmen erkannt", len(mapper.org_mapping))
            met_cols[3].metric("Orte erkannt", len(mapper.loc_mapping))

            # Tracking: welche Begriffe wurden bereits gelernt (für Button-Feedback)
            if "learned_this_session" not in st.session_state:
                st.session_state["learned_this_session"] = set()

            # Details in Expander — mit Korrektur-Buttons
            if total_entities > 0:
                with st.expander(f"Geschwärzte Entities ({total_entities} gesamt) — klicke um Korrekturen zu lernen", expanded=True):
                    st.caption("Klicke 'Nie schwärzen' um einen Begriff dauerhaft von der Schwärzung auszunehmen.")

                    all_redacted = []
                    for original, placeholder in mapper.person_mapping.items():
                        all_redacted.append((original, "PER", placeholder))
                    for original, placeholder in mapper.org_mapping.items():
                        all_redacted.append((original, "ORG", placeholder))
                    for original, placeholder in mapper.loc_mapping.items():
                        all_redacted.append((original, "LOC", placeholder))

                    for original, label, placeholder in all_redacted:
                        btn_key = f"learn_never_{label}_{original}"
                        already_learned = btn_key in st.session_state.get("learned_this_session", set())
                        col_info, col_btn = st.columns([5, 1])
                        label_icons = {"PER": "Person", "ORG": "Firma", "LOC": "Ort"}
                        col_info.text(f"  [{label_icons.get(label, label)}] {placeholder} = '{original}'")
                        if already_learned:
                            col_btn.button("Gelernt", key=btn_key, disabled=True)
                        else:
                            if col_btn.button("Nie schwärzen", key=btn_key):
                                add_never_redact(original)
                                st.session_state["learned_this_session"].add(btn_key)
                                st.toast(f"'{original}' wird ab sofort nie mehr geschwärzt.")
                                st.rerun()

            if mapper.skipped_whitelist:
                unique_skipped = set((t, l) for t, l in mapper.skipped_whitelist)
                with st.expander(f"Nicht geschwärzt — Whitelist ({len(unique_skipped)} Begriffe)"):
                    st.caption("Klicke 'Doch schwärzen' um einen Whitelist-Begriff dauerhaft zu schwärzen.")
                    for text, label in sorted(unique_skipped):
                        btn_key = f"learn_always_wl_{label}_{text}"
                        already_learned = btn_key in st.session_state.get("learned_this_session", set())
                        col_info, col_btn = st.columns([5, 1])
                        col_info.text(f"  [{label}] '{text}'")
                        if already_learned:
                            col_btn.button("Gelernt", key=btn_key, disabled=True)
                        else:
                            if col_btn.button("Doch schwärzen", key=btn_key):
                                add_always_redact(text, label)
                                st.session_state["learned_this_session"].add(btn_key)
                                st.toast(f"'{text}' wird ab sofort immer geschwärzt.")
                                st.rerun()

            if mapper.skipped_org_juristic:
                unique_org = set((t, l) for t, l in mapper.skipped_org_juristic)
                with st.expander(f"Nicht geschwärzt — Juristische Personen ({len(unique_org)} Begriffe)"):
                    st.caption("Juristische Personen haben kein Recht auf Datenschutz (Modus: konservativ)")
                    for text, label in sorted(unique_org):
                        btn_key = f"learn_always_org_{text}"
                        already_learned = btn_key in st.session_state.get("learned_this_session", set())
                        col_info, col_btn = st.columns([5, 1])
                        col_info.text(f"  '{text}'")
                        if already_learned:
                            col_btn.button("Gelernt", key=btn_key, disabled=True)
                        else:
                            if col_btn.button("Doch schwärzen", key=btn_key):
                                add_always_redact(text, "ORG")
                                st.session_state["learned_this_session"].add(btn_key)
                                st.toast(f"'{text}' wird ab sofort immer geschwärzt.")
                                st.rerun()

            if mapper.skipped_low_confidence:
                unique_lc = set((t, l) for t, l, c in mapper.skipped_low_confidence)
                with st.expander(f"Nicht geschwärzt — geringe Confidence ({len(unique_lc)} Begriffe)"):
                    st.caption("Klicke 'Doch schwärzen' um einen Begriff dauerhaft zur Schwärzung hinzuzufügen.")
                    for text, label in sorted(unique_lc):
                        btn_key = f"learn_always_{label}_{text}"
                        already_learned = btn_key in st.session_state.get("learned_this_session", set())
                        col_info, col_btn = st.columns([5, 1])
                        col_info.text(f"  [{label}] '{text}'")
                        if already_learned:
                            col_btn.button("Gelernt", key=btn_key, disabled=True)
                        else:
                            if col_btn.button("Doch schwärzen", key=btn_key):
                                add_always_redact(text, label)
                                st.session_state["learned_this_session"].add(btn_key)
                                st.toast(f"'{text}' wird ab sofort immer geschwärzt.")
                                st.rerun()

            # Manuell hinzufügen
            st.markdown("---")
            with st.expander("Begriff manuell zur Schwärzung hinzufügen"):
                man_col1, man_col2, man_col3 = st.columns([3, 1, 1])
                manual_text = man_col1.text_input("Begriff", key="manual_add_text", placeholder="z.B. Dr. Mustermann")
                manual_label = man_col2.selectbox("Typ", ["PER", "ORG", "LOC"], key="manual_add_label")
                if man_col3.button("Hinzufügen", key="manual_add_btn"):
                    if manual_text.strip():
                        add_always_redact(manual_text.strip(), manual_label)
                        st.success(f"'{manual_text.strip()}' [{manual_label}] wird ab sofort immer geschwärzt.")
                        st.rerun()

            # Neu starten Button
            st.markdown("")
            if st.button("Neue Schwärzung starten", use_container_width=True):
                # Upload-Key erhöhen erzwingt neuen File-Uploader (auch in Safari)
                new_key = st.session_state.get("upload_key", 0) + 1
                st.session_state.clear()
                st.session_state["upload_key"] = new_key
                st.rerun()

        else:
            st.warning("Keine Dateien konnten verarbeitet werden.")

else:
    # Leerzustand
    st.markdown(
        """
        <div style="text-align: center; padding: 60px 20px; color: #888;">
            <p style="font-size: 48px; margin-bottom: 10px;">&#128194;</p>
            <p style="font-size: 18px;">Ziehen Sie Ihre Dokumente in das Upload-Feld oben</p>
            <p>Unterstützte Formate: <strong>PDF, DOCX, DOC, MSG</strong></p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================== FOOTER ====================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 12px;'>"
    "DSGVO-konforme Dokumenten-Schwärzung v2 &mdash; Alle Daten werden lokal verarbeitet"
    "</div>",
    unsafe_allow_html=True
)
