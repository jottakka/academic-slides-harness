from __future__ import annotations

import unicodedata
from pathlib import Path

import pdfplumber

from academic_slides_harness.core.models import SourceDocument, sha256_file


def inspect_pdf(path: Path) -> SourceDocument:
    resolved = path.resolve()
    with pdfplumber.open(resolved) as pdf:
        pages = len(pdf.pages)
    return SourceDocument(
        path=resolved,
        kind="pdf",
        pages=pages,
        sha256=sha256_file(resolved),
    )


def extract_pdf_page_text(
    path: Path,
    *,
    pages: list[int],
    max_chars_per_page: int,
) -> dict:
    resolved = path.resolve()
    selected_pages: list[dict] = []
    with pdfplumber.open(resolved) as pdf:
        page_count = len(pdf.pages)
        invalid_pages = [page for page in pages if page < 1 or page > page_count]
        if invalid_pages:
            raise ValueError(
                f"Page selection {invalid_pages} is outside PDF page count {page_count}."
            )
        for page_number in pages:
            raw_text = pdf.pages[page_number - 1].extract_text() or ""
            text = normalize_extracted_pdf_text(raw_text)
            truncated = len(text) > max_chars_per_page
            selected_pages.append(
                {
                    "page": page_number,
                    "text": text[:max_chars_per_page],
                    "char_count": len(text),
                    "truncated": truncated,
                }
            )
    return {
        "source_pdf": str(resolved),
        "page_count": page_count,
        "pages": selected_pages,
    }


def normalize_extracted_pdf_text(raw_text: str) -> str:
    """Return compact JSON-safe text from PDF extraction output."""
    json_safe_text = "".join(
        " " if unicodedata.category(character) == "Cs" else character for character in raw_text
    )
    return " ".join(json_safe_text.split())
