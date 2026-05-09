from __future__ import annotations

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
) -> list[ScreenshotArtifact]:
    resolved = options.resolved()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[ScreenshotArtifact] = []

    with fitz.open(pdf_path) as document:
        for page_number in pages:
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(resolved.scale, resolved.scale),
                alpha=False,
            )
            output_path = output_dir / f"{target}-p{page_number}-{resolved.dpi}dpi.png"
            pixmap.save(output_path)
            artifacts.append(
                ScreenshotArtifact.from_file(
                    path=output_path,
                    target=target,
                    page=page_number,
                    width=pixmap.width,
                    height=pixmap.height,
                    dpi=resolved.dpi,
                    scale=resolved.scale,
                    zoom=resolved.zoom,
                )
            )
    return artifacts


def render_zoom_crop(
    *,
    pdf_path: Path,
    output_dir: Path,
    target: Literal["source_pdf", "deck_pdf"],
    page: int,
    crop: CropBox,
    options: RenderOptions,
) -> ScreenshotArtifact:
    resolved = options.resolved()
    output_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as document:
        pdf_page = document.load_page(page - 1)
        clip = _resolve_crop(crop, pdf_page.rect)
        zoomed_scale = resolved.scale * resolved.zoom
        pixmap = pdf_page.get_pixmap(
            matrix=fitz.Matrix(zoomed_scale, zoomed_scale),
            clip=clip,
            alpha=False,
        )
        output_path = output_dir / f"{target}-p{page}-crop-{resolved.dpi}dpi-z{resolved.zoom:g}.png"
        pixmap.save(output_path)
        return ScreenshotArtifact.from_file(
            path=output_path,
            target=target,
            page=page,
            width=pixmap.width,
            height=pixmap.height,
            dpi=resolved.dpi,
            scale=resolved.scale,
            zoom=resolved.zoom,
        )


def _resolve_crop(crop: CropBox, page_rect: fitz.Rect) -> fitz.Rect:
    if crop.normalized:
        x0 = page_rect.x0 + crop.x * page_rect.width
        y0 = page_rect.y0 + crop.y * page_rect.height
        x1 = x0 + crop.width * page_rect.width
        y1 = y0 + crop.height * page_rect.height
        return fitz.Rect(x0, y0, x1, y1)
    return fitz.Rect(crop.x, crop.y, crop.x + crop.width, crop.y + crop.height)
