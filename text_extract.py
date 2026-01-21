import sys
import os
# Ensure local libraries are found first
lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

import pdfplumber
# from docx import Document

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or " "
            return text
    elif file_path.endswith('.docx'):
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    else:
        raise ValueError("Unsupported file format")