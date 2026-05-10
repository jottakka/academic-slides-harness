from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageStat

from academic_slides_harness.mcp.server import (
    compile_rendered_beamer,
    create_run,
    ingest_source,
    list_visual_artifacts,
    plan_deck,
    render_beamer,
    render_slide_preview,
    render_source_preview,
    render_zoom_crop,
    validate_run,
)
from academic_slides_harness.render.tectonic import find_tectonic_executable

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sources"
OPEN_ACCESS_CHAPTER = FIXTURE_DIR / "springer-elements-robotics-ch12-image-processing.pdf"


@pytest.mark.latex
def test_open_access_image_processing_chapter_to_visual_deck_e2e(tmp_path: Path) -> None:
    if find_tectonic_executable() is None:
        pytest.skip("Tectonic executable is not available")

    assert OPEN_ACCESS_CHAPTER.is_file()

    run_result = create_run(base_dir=str(tmp_path / "runs"), title="Image Processing Chapter 12")
    assert run_result.ok is True
    run_dir = Path(run_result.structured_content["run_dir"])
    screenshots_dir = run_dir / "screenshots"

    ingest_result = ingest_source(source_path=str(OPEN_ACCESS_CHAPTER))
    assert ingest_result.ok is True
    assert ingest_result.structured_content["kind"] == "pdf"
    assert ingest_result.structured_content["pages"] == 17
    assert len(ingest_result.structured_content["sha256"]) == 64

    source_preview_result = render_source_preview(
        source_pdf=str(OPEN_ACCESS_CHAPTER),
        output_dir=str(screenshots_dir),
        pages="1,4",
        resolution="review",
    )
    assert source_preview_result.ok is True
    assert len(source_preview_result.structured_content["artifacts"]) == 2
    source_preview_artifacts = source_preview_result.structured_content["artifacts"]
    source_preview_by_page = {artifact["page"]: artifact for artifact in source_preview_artifacts}
    for artifact in source_preview_result.structured_content["artifacts"]:
        _assert_visual_artifact_has_ink(artifact, min_ink_ratio=0.01)

    source_crop_result = render_zoom_crop(
        pdf_path=str(OPEN_ACCESS_CHAPTER),
        output_dir=str(screenshots_dir),
        target="source_pdf",
        page=4,
        crop={"x": 0.05, "y": 0.42, "width": 0.9, "height": 0.36, "normalized": True},
        resolution="review",
        zoom=2.5,
    )
    assert source_crop_result.ok is True
    source_crop_artifact = source_crop_result.structured_content["artifact"]
    assert source_crop_artifact["width"] > source_preview_by_page[4]["width"]
    assert source_crop_artifact["height"] > source_preview_by_page[4]["height"] * 0.8
    _assert_visual_artifact_has_ink(
        source_crop_artifact,
        min_ink_ratio=0.02,
        min_stddev=20.0,
    )

    excerpts = [_extract_page_text(OPEN_ACCESS_CHAPTER, page_index) for page_index in (0, 2, 4)]
    assert "Image Processing" in excerpts[0]
    assert any("digital image processing" in excerpt.lower() for excerpt in excerpts)

    plan_result = plan_deck(
        title="Image Processing Chapter 12",
        excerpts=excerpts,
        max_slides=3,
    )
    assert plan_result.ok is True
    slides = plan_result.structured_content["slides"]
    assert len(slides) == 3
    assert all(slide["source_excerpt"] for slide in slides)

    beamer_result = render_beamer(
        output_dir=str(run_dir / "rendered"),
        title=plan_result.structured_content["title"],
        slides=slides,
    )
    assert beamer_result.ok is True
    tex_path = Path(beamer_result.structured_content["deck_tex"])
    assert tex_path.is_file()

    compile_result = compile_rendered_beamer(
        tex_path=str(tex_path),
        output_dir=str(run_dir / "compiled"),
    )
    assert compile_result.ok is True, compile_result.content_text
    deck_pdf = Path(compile_result.structured_content["pdf_path"])
    assert deck_pdf.is_file()
    with fitz.open(deck_pdf) as document:
        assert document.page_count == 4

    deck_preview_result = render_slide_preview(
        deck_pdf=str(deck_pdf),
        output_dir=str(screenshots_dir),
        slides="1-4",
        resolution="review",
    )
    assert deck_preview_result.ok is True
    assert len(deck_preview_result.structured_content["artifacts"]) == 4
    deck_preview_artifacts = deck_preview_result.structured_content["artifacts"]
    deck_preview_by_page = {artifact["page"]: artifact for artifact in deck_preview_artifacts}
    for artifact in deck_preview_artifacts:
        _assert_visual_artifact_has_ink(artifact, min_ink_ratio=0.003)

    deck_crop_result = render_zoom_crop(
        pdf_path=str(deck_pdf),
        output_dir=str(screenshots_dir),
        target="deck_pdf",
        page=2,
        crop={"x": 0.06, "y": 0.16, "width": 0.88, "height": 0.72, "normalized": True},
        resolution="review",
        zoom=2.0,
    )
    assert deck_crop_result.ok is True
    deck_crop_artifact = deck_crop_result.structured_content["artifact"]
    assert deck_crop_artifact["width"] > deck_preview_by_page[2]["width"]
    assert deck_crop_artifact["height"] > deck_preview_by_page[2]["height"]
    _assert_visual_artifact_has_ink(deck_crop_artifact)

    artifacts_result = list_visual_artifacts(screenshots_dir=str(screenshots_dir))
    assert artifacts_result.ok is True
    artifacts = artifacts_result.structured_content["artifacts"]
    assert len(artifacts) == 8
    assert {artifact["target"] for artifact in artifacts} == {"source_pdf", "deck_pdf"}
    assert all(artifact["sha256"] for artifact in artifacts)
    assert all(Path(artifact["path"]).is_absolute() for artifact in artifacts)
    assert all(Path(artifact["path"]).with_suffix(".png.json").is_file() for artifact in artifacts)
    assert any(artifact["zoom"] == 2.5 for artifact in artifacts)
    assert any(artifact["zoom"] == 2.0 for artifact in artifacts)

    validation_result = validate_run(run_dir=str(run_dir))
    assert validation_result.ok is True


def _extract_page_text(pdf_path: Path, page_index: int) -> str:
    with fitz.open(pdf_path) as document:
        return document.load_page(page_index).get_text()


def _assert_visual_artifact_has_ink(
    artifact: dict,
    *,
    min_ink_ratio: float = 0.005,
    max_ink_ratio: float = 0.65,
    min_stddev: float = 8.0,
) -> None:
    image_path = Path(artifact["path"])
    assert image_path.is_file()

    with Image.open(image_path) as image:
        assert image.format == "PNG"
        width, height = image.size
        assert artifact["width"] == width
        assert artifact["height"] == height
        grayscale = image.convert("L")
        histogram = grayscale.histogram()

    total_pixels = sum(histogram)
    ink_pixels = sum(histogram[:245])
    ink_ratio = ink_pixels / total_pixels
    assert min_ink_ratio <= ink_ratio <= max_ink_ratio
    assert ImageStat.Stat(grayscale).stddev[0] >= min_stddev
