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
        dpi = self.dpi or PRESET_DPI[self.resolution or "review"]
        scale = self.scale if self.scale is not None else dpi / 72
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
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(token))
        return sorted(dict.fromkeys(pages))
    return sorted(dict.fromkeys(int(page) for page in selection))
