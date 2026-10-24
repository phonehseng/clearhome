"""Turn an uploaded lease (PDF, Word or text file) into plain text. No AI involved.

Scanned PDFs (photos of paper) have no text layer, so they come back empty.
"""
import io
import os

from docx import Document
from pypdf import PdfReader

SUPPORTED = (".pdf", ".docx", ".txt")


def extract_text(filename, data):
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if ext == ".docx":
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts).strip()
    if ext == ".txt":
        return data.decode("utf-8", errors="replace").strip()
    raise ValueError(f"Unsupported file type. Please upload one of: {', '.join(SUPPORTED)}")
