from __future__ import annotations

from pathlib import Path

import pdfplumber

from academic_slides_harness.core.models import SourceDocument, sha256_bytes


def inspect_pdf(path: Path) -> SourceDocument:
    resolved = path.resolve()
    with pdfplumber.open(resolved) as pdf:
        pages = len(pdf.pages)
    return SourceDocument(
        path=resolved,
        kind="pdf",
        pages=pages,
        sha256=sha256_bytes(resolved.read_bytes()),
    )
