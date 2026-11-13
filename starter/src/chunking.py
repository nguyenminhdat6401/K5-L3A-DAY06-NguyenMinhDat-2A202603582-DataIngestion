"""Implement fixed-size and structure-aware chunking."""
import hashlib

from .models import Chunk, DocumentPage

def make_chunk(
    page: DocumentPage,
    start: int,
    end: int,
) -> Chunk:
    text = page.text[start:end]

    identity = (
        f"{page.document_id}|{page.page}|"
        f"{start}|{end}|{text}"
    )

    chunk_id = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    return Chunk(
        chunk_id=chunk_id,
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata={
            **page.metadata,
            "char_start": start,
            "char_end": end,
        },
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """TODO: split text into overlapping windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be positive.")

    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < size.")

    chunks = []
    start = 0

    while start < len(page.text):
        end = min(start + size, len(page.text))

        chunks.append(make_chunk(page, start, end))

        if end == len(page.text):
            break

        start = end - overlap

    return chunks



def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """TODO: group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive.")

    text = page.text
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_size, len(text))

        if end < len(text):
            paragraph_break = text.rfind(
                "\n\n", start, end
            )

            if paragraph_break > start:
                end = paragraph_break + 2

            else:
                sentence_break = max(
                    text.rfind(mark, start, end)
                    for mark in (". ", "? ", "! ")
                )

                if sentence_break > start:
                    end = sentence_break + 2

                else:
                    word_break = text.rfind(
                        " ", start, end
                    )

                    if word_break > start:
                        end = word_break + 1

        chunks.append(make_chunk(page, start, end))
        start = end

    return chunks
