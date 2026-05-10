from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

PRESET_DPI = {
    "fast": 72,
    "review": 144,
    "print": 300,
}


@dataclass(frozen=True)
class CropBox:
    x: float
    y: float
    width: float
    height: float
    normalized: bool = True

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Crop width and height must be positive.")


@dataclass(frozen=True)
class ResolvedRenderOptions:
    dpi: int
    scale: float
    zoom: float
    output_format: Literal["png"]


@dataclass(frozen=True)
class RenderOptions:
    resolution: Literal["fast", "review", "print"] | None = "review"
    dpi: int | None = None
    scale: float | None = None
    zoom: float = 1.0
    output_format: Literal["png"] = "png"

    def resolved(self) -> ResolvedRenderOptions:
        preset = self.resolution or "review"
        if preset not in PRESET_DPI:
            raise ValueError("resolution must be one of: fast, review, print")
        dpi = self.dpi or PRESET_DPI[preset]
        scale = self.scale if self.scale is not None else dpi / 72
        if dpi <= 0:
            raise ValueError("dpi must be positive")
        if scale <= 0:
            raise ValueError("scale must be positive")
        if self.zoom <= 0:
            raise ValueError("zoom must be positive")
        if self.output_format != "png":
            raise ValueError("output_format must be png")
        return ResolvedRenderOptions(
            dpi=dpi,
            scale=float(scale),
            zoom=float(self.zoom),
            output_format=self.output_format,
        )


def parse_page_selection(selection: str | Iterable[int]) -> list[int]:
    if isinstance(selection, str):
        pages: list[int] = []
        for part in selection.split(","):
            token = part.strip()
            if not token:
                continue
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                if end < start:
                    raise ValueError("page selection ranges must be ascending")
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(token))
        return _validate_pages(pages)
    return _validate_pages(int(page) for page in selection)


def _validate_pages(pages: Iterable[int]) -> list[int]:
    selected = sorted(dict.fromkeys(pages))
    if not selected:
        raise ValueError("page selection must include at least one page")
    if any(page < 1 for page in selected):
        raise ValueError("page selection must use one-based positive page numbers")
    return selected
