"""
Basic document text extraction.

The assignment explicitly says production-grade OCR/parsing isn't required,
so this stays simple: plain-text extraction from PDFs (pypdf) and pass-
through for typed text / pasted email bodies. Swap this module out for a
real OCR pipeline (e.g. Textract, Azure Doc Intelligence) if this ever needs
to handle scanned/handwritten complaint letters in production.
"""
import io

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF's text layer (no OCR for scanned images)."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages_text).strip()
    if not text:
        raise ValueError(
            "No extractable text found in PDF. This demo does not include OCR, "
            "so scanned/image-only PDFs aren't supported — please use a text-based PDF."
        )
    return text
