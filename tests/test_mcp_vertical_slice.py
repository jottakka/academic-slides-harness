from pathlib import Path

import fitz

from academic_slides_harness.mcp.server import (
    compile_rendered_beamer,
    ingest_source,
    list_visual_artifacts,
    plan_deck,
    render_beamer,
    render_slide_preview,
    render_zoom_crop,
)
from academic_slides_harness.render.tectonic import find_tectonic_executable


def test_mcp_pdf_to_visual_artifacts_vertical_slice(tmp_path: Path) -> None:
    source_pdf = _make_source_pdf(tmp_path / "source.pdf")

    ingest_result = ingest_source(source_path=str(source_pdf))
    assert ingest_result.ok is True
    assert ingest_result.structured_content["pages"] == 1

    source_text = _extract_pdf_text(source_pdf)
    plan_result = plan_deck(title="Vertical Slice", excerpts=[source_text], max_slides=1)
    assert plan_result.ok is True
    assert len(plan_result.structured_content["slides"]) == 1

    beamer_result = render_beamer(
        output_dir=str(tmp_path / "rendered"),
        title=plan_result.structured_content["title"],
        slides=plan_result.structured_content["slides"],
    )
    assert beamer_result.ok is True
    tex_path = Path(beamer_result.structured_content["deck_tex"])
    assert tex_path.exists()

    deck_pdf = tmp_path / "compiled" / "deck.pdf"
    if find_tectonic_executable() is not None:
        compile_result = compile_rendered_beamer(
            tex_path=str(tex_path),
            output_dir=str(tmp_path / "compiled"),
        )
        assert compile_result.ok is True
        deck_pdf = Path(compile_result.structured_content["pdf_path"])
    else:
        deck_pdf.parent.mkdir(parents=True)
        _make_deck_pdf(deck_pdf)

    screenshots_dir = tmp_path / "screenshots"
    preview_result = render_slide_preview(
        deck_pdf=str(deck_pdf),
        output_dir=str(screenshots_dir),
        slides="1",
        resolution="fast",
    )
    assert preview_result.ok is True
    assert len(preview_result.structured_content["artifacts"]) == 1

    crop_result = render_zoom_crop(
        pdf_path=str(deck_pdf),
        output_dir=str(screenshots_dir),
        target="deck_pdf",
        page=1,
        crop={"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5, "normalized": True},
        resolution="fast",
        zoom=2.0,
    )
    assert crop_result.ok is True

    list_result = list_visual_artifacts(screenshots_dir=str(screenshots_dir))
    assert list_result.ok is True
    artifacts = list_result.structured_content["artifacts"]
    assert len(artifacts) == 2
    assert {artifact["target"] for artifact in artifacts} == {"deck_pdf"}
    assert {artifact["page"] for artifact in artifacts} == {1}
    assert {artifact["dpi"] for artifact in artifacts} == {72}
    assert {artifact["scale"] for artifact in artifacts} == {1.0}
    assert {artifact["zoom"] for artifact in artifacts} == {1.0, 2.0}
    assert all(Path(artifact["path"]).exists() for artifact in artifacts)
    assert all(artifact["sha256"] for artifact in artifacts)


def _make_source_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=420, height=320)
    page.insert_text(
        (42, 84),
        "Evidence-backed slide systems need deterministic ingestion. "
        "They also need visual previews for review.",
        fontsize=14,
    )
    doc.save(path)
    doc.close()
    return path


def _make_deck_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=420, height=320)
    page.insert_text((42, 84), "Fallback compiled deck preview", fontsize=18)
    doc.save(path)
    doc.close()
    return path


def _extract_pdf_text(path: Path) -> str:
    with fitz.open(path) as document:
        return document.load_page(0).get_text()
