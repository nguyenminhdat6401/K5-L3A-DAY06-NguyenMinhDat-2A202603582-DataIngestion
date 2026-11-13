"""Read and normalize source data. TODO: implement functions."""
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage



def load_pdf(path: Path, document_id: str, source: str, errors: list[dict] | None = None,) -> list[DocumentPage]:
    """TODO: extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    """Extract physical PDF pages, numbered from 1.

    Record unreadable or empty pages in errors when supplied.
    Otherwise, raise an exception.
    """
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(path)
    pages = []

    for page_number, pdf_page in enumerate(reader.pages, start=1):
        try:
            raw_text = pdf_page.extract_text(extraction_mode="layout") or ""
            text = normalize_text(raw_text)

            if not text:
                raise ValueError("Empty page or OCR required.")

        except Exception as exc:
            if errors is None:
                raise RuntimeError(
                    f"Cannot extract page {page_number}"
                ) from exc

            errors.append(
                {
                    "document_id": document_id,
                    "page": page_number,
                    "error": str(exc),
                }
            )
            continue

        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_number,
                text=text,
                metadata={
                    "language": "en",
                    "document_type": "textbook",
                },
            )
        )

    return pages


def normalize_text(text: str) -> str:
    """TODO: normalize Unicode and whitespace without discarding useful structure."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")

    paragraphs = re.split(r"\n\s*\n", text)

    cleaned = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if paragraph:
            cleaned.append(paragraph)

    return "\n\n".join(cleaned)
