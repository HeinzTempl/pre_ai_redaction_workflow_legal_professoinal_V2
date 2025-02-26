import openai
import os

# Setze deinen API-Key hier ODER als Umgebungsvariable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "Paste_YOUR_API_KEY_HERE")

def redact_text_api(text):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": (
                "Your task is to redact sensitive information from a document (mainly in german language) while preserving the original structure, language, and formatting. "
                "Do NOT translate, rephrase, or change any content. Only replace personal data (e.g., names of persons and/or legal entities, addresses, phone numbers, email addresses, commercial register numbers) "
                "with placeholders like '[REDACTED]'."
            )},
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    redacted_text = response.choices[0].message.content
    print("Redacted Text (API):\n", redacted_text)

    return redacted_text