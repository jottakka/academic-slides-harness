from __future__ import annotations

import errno
import json
from pathlib import Path
from typing import Literal

import fitz

from academic_slides_harness.core.models import ScreenshotArtifact
from academic_slides_harness.visualize.options import CropBox, RenderOptions


def render_pdf_pages(
    *,
    pdf_path: Path,
    output_dir: Path,
    target: Literal["source_pdf", "deck_pdf"],
    pages: list[int],
    options: RenderOptions,
    overwrite: bool = False,
) -> list[ScreenshotArtifact]:
    resolved = options.resolved()
    _ensure_pdf_file(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[ScreenshotArtifact] = []

    with fitz.open(pdf_path) as document:
        _validate_pages_within_document(pages=pages, page_count=document.page_count)
        for page_number in pages:
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(resolved.scale, resolved.scale),
                alpha=False,
            )
            output_path = output_dir / f"{target}-p{page_number}-{resolved.dpi}dpi.png"
            _ensure_can_write_artifact(output_path=output_path, overwrite=overwrite)
            pixmap.save(output_path)
            artifact = ScreenshotArtifact.from_file(
                path=output_path,
                target=target,
                page=page_number,
                width=pixmap.width,
                height=pixmap.height,
                dpi=resolved.dpi,
                scale=resolved.scale,
                zoom=resolved.zoom,
            )
            _write_sidecar(artifact)
            artifacts.append(artifact)
    return artifacts


def render_zoom_crop(
    *,
    pdf_path: Path,
    output_dir: Path,
    target: Literal["source_pdf", "deck_pdf"],
    page: int,
    crop: CropBox,
    options: RenderOptions,
    overwrite: bool = False,
) -> ScreenshotArtifact:
    resolved = options.resolved()
    _ensure_pdf_file(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        _validate_pages_within_document(pages=[page], page_count=document.page_count)
        pdf_page = document.load_page(page - 1)
        clip = _resolve_crop(crop, pdf_page.rect)
        zoomed_scale = resolved.scale * resolved.zoom
        pixmap = pdf_page.get_pixmap(
            matrix=fitz.Matrix(zoomed_scale, zoomed_scale),
            clip=clip,
            alpha=False,
        )
        output_path = output_dir / f"{target}-p{page}-crop-{resolved.dpi}dpi-z{resolved.zoom:g}.png"
        _ensure_can_write_artifact(output_path=output_path, overwrite=overwrite)
        pixmap.save(output_path)
        artifact = ScreenshotArtifact.from_file(
            path=output_path,
            target=target,
            page=page,
            width=pixmap.width,
            height=pixmap.height,
            dpi=resolved.dpi,
            scale=resolved.scale,
            zoom=resolved.zoom,
        )
        _write_sidecar(artifact)
        return artifact


def _resolve_crop(crop: CropBox, page_rect: fitz.Rect) -> fitz.Rect:
    if crop.normalized:
        x0 = page_rect.x0 + crop.x * page_rect.width
        y0 = page_rect.y0 + crop.y * page_rect.height
        x1 = x0 + crop.width * page_rect.width
        y1 = y0 + crop.height * page_rect.height
        rect = fitz.Rect(x0, y0, x1, y1)
    else:
        rect = fitz.Rect(crop.x, crop.y, crop.x + crop.width, crop.y + crop.height)
    if rect.is_empty or not page_rect.contains(rect):
        raise ValueError("Crop is outside page bounds.")
    return rect


def _ensure_pdf_file(pdf_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")


def _validate_pages_within_document(*, pages: list[int], page_count: int) -> None:
    invalid_pages = [page for page in pages if page < 1 or page > page_count]
    if invalid_pages:
        raise ValueError(f"Page selection {invalid_pages} is outside PDF page count {page_count}.")


def _ensure_can_write_artifact(*, output_path: Path, overwrite: bool) -> None:
    if output_path.exists() and not overwrite:
        raise FileExistsError(errno.EEXIST, "PNG artifact already exists", str(output_path))


def _write_sidecar(artifact: ScreenshotArtifact) -> None:
    sidecar_path = artifact.path.with_suffix(f"{artifact.path.suffix}.json")
    sidecar_path.write_text(
        json.dumps(artifact.to_structured_content(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
