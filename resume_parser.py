import pdfplumber
from docx import Document

def parse_resume(file_path: str) -> str:
    """
    Extract plain text from a PDF or DOCX resume.
    Returns cleaned text for prompt injection.
    """
    text = ""

    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    elif file_path.lower().endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"

    else:
        raise ValueError("Unsupported resume format. Use PDF or DOCX.")

    return text.strip()
