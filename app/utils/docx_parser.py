from io import BytesIO

from docx import Document


def extract_text_from_docx(docx_bytes: bytes) -> str:
    doc = Document(BytesIO(docx_bytes))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]
    return "\n".join(paragraphs)
