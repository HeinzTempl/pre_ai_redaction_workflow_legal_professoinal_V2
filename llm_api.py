import openai
import os

# Setze deinen API-Key hier ODER als Umgebungsvariable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "Paste_YOUR_API_KEY_HERE")

def redact_text_api(text):
    """
    Sendet Text an die OpenAI API zur Schwärzung sensibler personenbezogener Daten.
    Optimiert für deutsche juristische Dokumente.
    """
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": (
                "Du bist ein Datenschutz-Spezialist für deutsche juristische Dokumente. "
                "Deine Aufgabe ist es, personenbezogene Daten im Text durch '[REDACTED]' zu ersetzen.\n\n"
                "WAS GESCHWÄRZT WERDEN MUSS:\n"
                "- Vor- und Nachnamen natürlicher Personen\n"
                "- Firmennamen und Unternehmensbezeichnungen\n"
                "- Straßen, Hausnummern, PLZ und Orte (vollständige Adressen)\n"
                "- E-Mail-Adressen und Telefonnummern\n"
                "- IBAN, Kontonummern, BIC\n"
                "- Steuernummern, Sozialversicherungsnummern\n"
                "- Geburtsdaten\n"
                "- Handelsregisternummern (HRA/HRB)\n"
                "- Aktenzeichen die Rückschlüsse auf Parteien erlauben\n"
                "- Grundbuchnummern\n\n"
                "WAS NICHT GESCHWÄRZT WERDEN DARF:\n"
                "- Gerichtsbezeichnungen (z.B. 'Amtsgericht München', 'Landesarbeitsgericht Wien')\n"
                "- Gesetzesbezeichnungen und Paragraphen (z.B. '§ 823 BGB', 'Art. 6 DSGVO')\n"
                "- Allgemeine juristische Begriffe und Fachbegriffe\n"
                "- Datumsangaben die keine Geburtsdaten sind (z.B. Urteilsdaten, Fristen)\n"
                "- Behördenbezeichnungen\n"
                "- Berufsbezeichnungen ohne Namen\n\n"
                "REGELN:\n"
                "- Originalsprache, Struktur und Formatierung EXAKT beibehalten\n"
                "- NICHT übersetzen, umformulieren oder zusammenfassen\n"
                "- Nur '[REDACTED]' als Platzhalter verwenden\n"
                "- Im Zweifel: lieber NICHT schwärzen (weniger False Positives)"
            )},
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    redacted_text = response.choices[0].message.content
    return redacted_text
