from pathlib import Path

import fitz

from academic_slides_harness.ingest.pdf import inspect_pdf


def test_inspect_pdf_reads_real_page_count_and_hash(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=120)
    doc.new_page(width=200, height=120)
    doc.save(pdf_path)
    doc.close()

    source = inspect_pdf(pdf_path)

    assert source.path == pdf_path.resolve()
    assert source.kind == "pdf"
    assert source.pages == 2
    assert source.sha256
