from pathlib import Path

import fitz
import pytest
from PIL import Image

from academic_slides_harness.visualize.options import CropBox, RenderOptions, parse_page_selection
from academic_slides_harness.visualize.preview import render_pdf_pages, render_zoom_crop
from academic_slides_harness.visualize.sanitize import VisualAssetError, sanitize_visual_asset


def _make_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((72, 96), "Academic Slides Harness", fontsize=24)
    page.draw_rect(fitz.Rect(40, 40, 200, 160), color=(1, 0, 0), width=2)
    doc.save(path)
    doc.close()
    return path


def _make_image(path: Path, *, size: tuple[int, int] = (32, 24), mode: str = "RGB") -> Path:
    Image.new(mode, size, color=(80, 120, 160)).save(path)
    return path


def test_parse_page_selection_accepts_ranges_and_lists() -> None:
    assert parse_page_selection("1-3,5") == [1, 2, 3, 5]
    assert parse_page_selection([2, 4]) == [2, 4]


@pytest.mark.parametrize("selection", ["0", "3-1", "", [1, 0]])
def test_parse_page_selection_rejects_invalid_pages(selection: str | list[int]) -> None:
    with pytest.raises(ValueError, match="page selection"):
        parse_page_selection(selection)


def test_render_options_resolve_named_presets() -> None:
    fast = RenderOptions(resolution="fast").resolved()
    review = RenderOptions(resolution="review").resolved()
    explicit = RenderOptions(dpi=200, scale=2.5).resolved()

    assert fast.dpi == 72
    assert review.dpi == 144
    assert explicit.dpi == 200
    assert explicit.scale == 2.5


@pytest.mark.parametrize(
    "options",
    [
        RenderOptions(resolution="bad"),
        RenderOptions(dpi=-1),
        RenderOptions(scale=0),
        RenderOptions(zoom=0),
    ],
)
def test_render_options_reject_invalid_values(options: RenderOptions) -> None:
    with pytest.raises(ValueError):
        options.resolved()


def test_crop_box_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="positive"):
        CropBox(x=0, y=0, width=-1, height=1)


def test_sanitize_visual_asset_preserves_valid_png_metadata(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "source.png")

    asset = sanitize_visual_asset(source_path=source, output_dir=tmp_path / "assets")

    content = asset.to_structured_content()
    assert asset.path.is_file()
    assert content["source_path"] == str(source.resolve())
    assert content["path"] == str(asset.path)
    assert content["width"] == 32
    assert content["height"] == 24
    assert content["format"] == "PNG"
    assert content["mode"] == "RGB"
    assert content["converted"] is False
    assert content["sha256"]
    assert content["source_sha256"]


def test_sanitize_visual_asset_preserves_valid_jpeg_metadata(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "source.jpg")

    asset = sanitize_visual_asset(source_path=source, output_dir=tmp_path / "assets")

    assert asset.path.suffix == ".jpg"
    assert asset.format == "JPEG"
    assert asset.converted is False
    assert asset.width == 32
    assert asset.height == 24


def test_sanitize_visual_asset_converts_readable_non_png_jpeg_to_png(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "source.bmp")

    asset = sanitize_visual_asset(source_path=source, output_dir=tmp_path / "assets")

    assert asset.path.suffix == ".png"
    assert asset.converted is True
    assert asset.format == "PNG"


def test_sanitize_visual_asset_rejects_corrupt_image(tmp_path: Path) -> None:
    source = tmp_path / "broken.png"
    source.write_text("not an image", encoding="utf-8")

    with pytest.raises(VisualAssetError) as error:
        sanitize_visual_asset(source_path=source, output_dir=tmp_path / "assets")

    assert error.value.kind == "invalid_visual_artifact"
    assert error.value.details["artifact_path"] == str(source.resolve())


def test_sanitize_visual_asset_rejects_tiny_image(tmp_path: Path) -> None:
    source = _make_image(tmp_path / "tiny.png", size=(8, 8))

    with pytest.raises(VisualAssetError) as error:
        sanitize_visual_asset(source_path=source, output_dir=tmp_path / "assets")

    assert error.value.kind == "image_too_small"
    assert error.value.details["width"] == 8
    assert error.value.details["height"] == 8
    assert error.value.details["min_width"] == 16
    assert error.value.details["min_height"] == 16


def test_render_pdf_pages_creates_real_png_artifacts(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")

    artifacts = render_pdf_pages(
        pdf_path=source,
        output_dir=tmp_path / "screens",
        target="source_pdf",
        pages=[1],
        options=RenderOptions(resolution="fast"),
    )

    assert len(artifacts) == 1
    assert artifacts[0].path.exists()
    assert artifacts[0].width > 0
    assert artifacts[0].height > 0
    assert artifacts[0].sha256


def test_render_pdf_pages_rejects_existing_artifact_by_default(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")
    output_dir = tmp_path / "screens"
    render_pdf_pages(
        pdf_path=source,
        output_dir=output_dir,
        target="source_pdf",
        pages=[1],
        options=RenderOptions(resolution="fast"),
    )

    with pytest.raises(FileExistsError, match="already exists"):
        render_pdf_pages(
            pdf_path=source,
            output_dir=output_dir,
            target="source_pdf",
            pages=[1],
            options=RenderOptions(resolution="fast"),
        )


def test_render_pdf_pages_allows_explicit_overwrite(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")
    output_dir = tmp_path / "screens"
    first = render_pdf_pages(
        pdf_path=source,
        output_dir=output_dir,
        target="source_pdf",
        pages=[1],
        options=RenderOptions(resolution="fast"),
    )

    second = render_pdf_pages(
        pdf_path=source,
        output_dir=output_dir,
        target="source_pdf",
        pages=[1],
        options=RenderOptions(resolution="fast"),
        overwrite=True,
    )

    assert second[0].path == first[0].path


def test_render_pdf_pages_rejects_missing_pdf(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="PDF not found"):
        render_pdf_pages(
            pdf_path=tmp_path / "missing.pdf",
            output_dir=tmp_path / "screens",
            target="source_pdf",
            pages=[1],
            options=RenderOptions(resolution="fast"),
        )


def test_render_pdf_pages_rejects_out_of_bounds_pages(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")

    with pytest.raises(ValueError, match="outside PDF page count"):
        render_pdf_pages(
            pdf_path=source,
            output_dir=tmp_path / "screens",
            target="source_pdf",
            pages=[2],
            options=RenderOptions(resolution="fast"),
        )


def test_render_zoom_crop_creates_larger_detail_artifact(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")

    artifact = render_zoom_crop(
        pdf_path=source,
        output_dir=tmp_path / "crops",
        target="source_pdf",
        page=1,
        crop=CropBox(x=0.0, y=0.0, width=0.5, height=0.5, normalized=True),
        options=RenderOptions(resolution="fast", zoom=2.0),
    )

    assert artifact.path.exists()
    assert artifact.zoom == 2.0
    assert artifact.width > 100
    assert artifact.height > 100


def test_render_zoom_crop_rejects_existing_artifact_by_default(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")
    output_dir = tmp_path / "crops"
    render_zoom_crop(
        pdf_path=source,
        output_dir=output_dir,
        target="source_pdf",
        page=1,
        crop=CropBox(x=0.0, y=0.0, width=0.5, height=0.5, normalized=True),
        options=RenderOptions(resolution="fast", zoom=2.0),
    )

    with pytest.raises(FileExistsError, match="already exists"):
        render_zoom_crop(
            pdf_path=source,
            output_dir=output_dir,
            target="source_pdf",
            page=1,
            crop=CropBox(x=0.0, y=0.0, width=0.5, height=0.5, normalized=True),
            options=RenderOptions(resolution="fast", zoom=2.0),
        )


def test_render_zoom_crop_rejects_crop_outside_page(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")

    with pytest.raises(ValueError, match="outside page bounds"):
        render_zoom_crop(
            pdf_path=source,
            output_dir=tmp_path / "crops",
            target="source_pdf",
            page=1,
            crop=CropBox(x=2.0, y=2.0, width=0.5, height=0.5, normalized=True),
            options=RenderOptions(resolution="fast", zoom=2.0),
        )
