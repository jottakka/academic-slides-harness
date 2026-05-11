import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from academic_slides_harness.mcp.server import list_visual_artifacts
from academic_slides_harness.visualize.options import RenderOptions
from academic_slides_harness.visualize.preview import render_pdf_pages
from academic_slides_harness.visualize.quality import assess_visual_quality


def test_visual_quality_flags_blank_image(tmp_path: Path) -> None:
    image_path = tmp_path / "blank.png"
    Image.new("RGB", (640, 360), "white").save(image_path)

    report = assess_visual_quality(image_path, context="source_crop")

    warning_kinds = {warning["kind"] for warning in report.to_structured_content()["warnings"]}
    assert "low_visual_density" in warning_kinds


def test_visual_quality_flags_low_contrast_image(tmp_path: Path) -> None:
    image_path = tmp_path / "low-contrast.png"
    image = Image.new("RGB", (640, 360), (128, 128, 128))
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 100, 540, 260), fill=(134, 134, 134))
    image.save(image_path)

    report = assess_visual_quality(image_path, context="source_crop")

    warning_kinds = {warning["kind"] for warning in report.to_structured_content()["warnings"]}
    assert "low_contrast" in warning_kinds


def test_visual_quality_flags_text_heavy_crop(tmp_path: Path) -> None:
    image_path = tmp_path / "text-heavy.png"
    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    for row in range(22):
        draw.text(
            (40, 24 + row * 20),
            "Figure text paragraph dominates this crop and should be cropped tighter.",
            fill="black",
        )
    image.save(image_path)

    report = assess_visual_quality(image_path, context="source_crop")

    warning_kinds = {warning["kind"] for warning in report.to_structured_content()["warnings"]}
    assert "text_heavy_crop" in warning_kinds


def test_visual_quality_allows_simple_figure_like_image(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 90, 390, 310), fill=(80, 80, 80))
    draw.rectangle((430, 90, 740, 310), fill=(180, 180, 180), outline="black", width=8)
    draw.line((80, 370, 740, 370), fill="black", width=6)
    image.save(image_path)

    report = assess_visual_quality(image_path, context="source_crop")

    assert report.to_structured_content()["ok"] is True
    assert report.to_structured_content()["warnings"] == []


def test_render_source_preview_includes_page_like_quality_warning(tmp_path: Path) -> None:
    pdf_path = _make_portrait_text_pdf(tmp_path / "source.pdf")

    artifacts = render_pdf_pages(
        pdf_path=pdf_path,
        output_dir=tmp_path / "screenshots",
        target="source_pdf",
        pages=[1],
        options=RenderOptions(resolution="fast"),
    )

    content = artifacts[0].to_structured_content()
    warning_kinds = {warning["kind"] for warning in content["quality"]["warnings"]}
    assert "page_like_snapshot" in warning_kinds
    assert "text_heavy_crop" in warning_kinds

    sidecar = json.loads(artifacts[0].path.with_suffix(".png.json").read_text(encoding="utf-8"))
    assert sidecar["quality"]["warnings"]

    listed = list_visual_artifacts(screenshots_dir=str(tmp_path / "screenshots"))
    listed_quality = listed.structured_content["artifacts"][0]["quality"]
    listed_warning_kinds = {warning["kind"] for warning in listed_quality["warnings"]}
    assert "page_like_snapshot" in listed_warning_kinds


def _make_portrait_text_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=300, height=520)
    for row in range(20):
        page.insert_text(
            (36, 60 + row * 18),
            "Dense source paragraph text should not be treated as a hero visual.",
            fontsize=9,
        )
    doc.save(path)
    doc.close()
    return path
