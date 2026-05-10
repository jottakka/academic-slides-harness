from pathlib import Path

import fitz
import pytest

from academic_slides_harness.visualize.options import CropBox, RenderOptions, parse_page_selection
from academic_slides_harness.visualize.preview import render_pdf_pages, render_zoom_crop


def _make_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((72, 96), "Academic Slides Harness", fontsize=24)
    page.draw_rect(fitz.Rect(40, 40, 200, 160), color=(1, 0, 0), width=2)
    doc.save(path)
    doc.close()
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
