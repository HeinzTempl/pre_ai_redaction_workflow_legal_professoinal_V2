# DSGVO/GDPR-Compliant Pre-AI Document Redaction Workflow

This project provides a pre-processing workflow for legal documents that ensures sensitive data is anonymized before being processed by a Language Model (LLM). Designed with the needs of lawyers, prosecutors, notaries, and legal departments in mind, the solution helps you maintain GDPR compliance by ensuring that only anonymized data is sent to external LLM providers.

## Overview

The workflow processes various document formats (DOCX, PDF, MSG) using a two-step approach:
1. **Regex-based Redaction:**  
   Standardized patterns (e.g., email addresses, phone numbers) are replaced with placeholder text.
2. **spaCy-based Redaction:**  
   Advanced NLP (using spaCy) detects complex entities such as person names and organizations, replacing them with placeholders like "Person A" or "Firma A".

Additionally, the solution provides an option to convert DOCX and MSG files to PDF for better processing accuracy. For cases where API-based redaction is required, an OpenAI API integration is available (with a GDPR-compliant data processing addendum).

## Getting Started

### Prerequisites

- **Python 3.7+**  
  Download and install Python from: https://www.python.org/downloads/

- **An IDE or Code Editor**  
  We recommend using [PyCharm](https://www.jetbrains.com/pycharm/) or Visual Studio Code for an optimal development experience.

### Installation

1. **Clone the Repository**  
   Open your terminal or command prompt and run:
   ```bash
   [git clone https://github.com/yourusername/your-repository-name.git
   cd your-repository-name](https://github.com/HeinzTempl/pre_ai_redaction_workflow_legal_professoinal_V2.git)
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

2.	Create a Virtual Environment (optional but recommended)
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

3.	Install Dependencies
Run the following commands in your terminal:
pip install the following packages

pip install python-docx
pip install spacy
pip install pymupdf
pip install openai
pip install regex
pip install unoconv
pip install reportlab
pip install extract-msg

Install the SpaCy libraries for German
SpaCy Lib:

python -m spacy download de_core_news_sm


5. 	Usage
	1.	Configure Your Environment
	•	Ensure that Microsoft Word (or an Office suite) is installed on your system if you plan to convert DOCX files to PDF.
	•	If you use the API-based redaction option, make sure you have set your OpenAI API key (either by setting the OPENAI_API_KEY environment variable or directly in the code).
	2.	Run the Script

To start the workflow, simply run:

python main.py

The script will prompt you for a folder path and ask if you want to convert DOCX and MSG files to PDF. Based on your selection, it will process the files accordingly:
	•	Option ‘j’ (yes): DOCX and MSG files are converted to PDF, then all PDFs are redacted.
	•	Option ‘n’ (no): Existing PDFs are redacted, and DOCX files are processed directly (MSG files are still converted to PDF for redaction).

	3.	Output

The redacted files are saved in a subfolder named redacted inside the input folder. Converted files (if applicable) are saved in a subfolder named converted.

Additional Information
	•	Local Redaction:
Uses a hybrid approach with regex and spaCy for anonymizing personal data, ensuring that sensitive information is not exposed during subsequent LLM processing.
	•	API Redaction:
An alternative integration with OpenAI’s API is available. This method complies with GDPR as it uses a Data Processing Addendum. More details can be found here: https://openai.com/policies/data-processing-addendum/.
	•	Network Paths:
The script supports both local and network paths, as long as the network drive is properly mounted and accessible.

License

[MIT License]

Contact

For any questions or feedback, please contact [Your Name] at [heinz@templ.com].
