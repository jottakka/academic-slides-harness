from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class LayoutOverflowRegion:
    label: str
    x: float
    y: float
    width: float
    height: float
    max_ink_ratio: float = 0.01
    normalized: bool = True
    ink_luminance_threshold: int = 185

    def to_structured_content(
        self,
        *,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> dict[str, Any]:
        content: dict[str, Any] = {
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "max_ink_ratio": self.max_ink_ratio,
            "normalized": self.normalized,
            "ink_luminance_threshold": self.ink_luminance_threshold,
        }
        if image_width is not None and image_height is not None:
            content["bbox_px"] = list(self.to_pixel_box(image_width, image_height))
        return content

    def to_pixel_box(self, image_width: int, image_height: int) -> tuple[int, int, int, int]:
        if self.normalized:
            x0 = round(self.x * image_width)
            y0 = round(self.y * image_height)
            x1 = round((self.x + self.width) * image_width)
            y1 = round((self.y + self.height) * image_height)
        else:
            x0 = round(self.x)
            y0 = round(self.y)
            x1 = round(self.x + self.width)
            y1 = round(self.y + self.height)
        return (
            max(0, min(image_width, x0)),
            max(0, min(image_height, y0)),
            max(0, min(image_width, x1)),
            max(0, min(image_height, y1)),
        )


@dataclass(frozen=True)
class LayoutOverflowWarning:
    kind: str
    severity: str
    message: str
    details: dict[str, Any]

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class LayoutOverflowReport:
    ok: bool
    image_path: Path
    width: int
    height: int
    regions: tuple[dict[str, Any], ...]
    warnings: tuple[LayoutOverflowWarning, ...]

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "image_path": str(self.image_path.resolve()),
            "width": self.width,
            "height": self.height,
            "regions": list(self.regions),
            "warnings": [warning.to_structured_content() for warning in self.warnings],
        }


def default_layout_overflow_regions() -> list[LayoutOverflowRegion]:
    return [
        LayoutOverflowRegion(
            label="center gutter",
            x=0.61,
            y=0.13,
            width=0.045,
            height=0.74,
            max_ink_ratio=0.015,
        )
    ]


def assess_layout_overflow(
    image_path: str | Path,
    *,
    regions: list[LayoutOverflowRegion],
) -> LayoutOverflowReport:
    resolved_path = Path(image_path).resolve()
    with Image.open(resolved_path) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        warnings: list[LayoutOverflowWarning] = []
        region_content: list[dict[str, Any]] = []
        for region in regions:
            bbox = region.to_pixel_box(width, height)
            region_metrics = _measure_region_ink(
                grayscale,
                bbox=bbox,
                threshold=region.ink_luminance_threshold,
            )
            content = region.to_structured_content(image_width=width, image_height=height)
            content.update(region_metrics)
            region_content.append(content)
            if region_metrics["ink_ratio"] > region.max_ink_ratio:
                warnings.append(
                    LayoutOverflowWarning(
                        kind="protected_region_ink",
                        severity="error",
                        message="Protected layout region contains visible content.",
                        details={
                            "label": region.label,
                            "bbox_px": list(bbox),
                            "ink_pixels": region_metrics["ink_pixels"],
                            "total_pixels": region_metrics["total_pixels"],
                            "ink_ratio": region_metrics["ink_ratio"],
                            "max_ink_ratio": region.max_ink_ratio,
                            "normalized": region.normalized,
                            "region": region.to_structured_content(),
                        },
                    )
                )
    return LayoutOverflowReport(
        ok=not warnings,
        image_path=resolved_path,
        width=width,
        height=height,
        regions=tuple(region_content),
        warnings=tuple(warnings),
    )


def parse_tex_box_warnings(log_text: str) -> dict[str, Any]:
    overfull_lines: list[dict[str, Any]] = []
    underfull_lines: list[dict[str, Any]] = []
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        overfull = re.search(
            r"Overfull\s+\\[hv]box\s+\((?P<excess>[-+]?\d+(?:\.\d+)?)pt too wide\)",
            line,
        )
        if overfull is not None:
            overfull_lines.append(
                {
                    "line": _tex_warning_line_number(line),
                    "excess_pt": float(overfull.group("excess")),
                    "message": line,
                }
            )
            continue
        underfull = re.search(
            r"Underfull\s+\\[hv]box\s+\(badness (?P<badness>\d+)\)",
            line,
        )
        if underfull is not None:
            underfull_lines.append(
                {
                    "line": _tex_warning_line_number(line),
                    "badness": int(underfull.group("badness")),
                    "message": line,
                }
            )
    return {
        "overfull_count": len(overfull_lines),
        "underfull_count": len(underfull_lines),
        "overfull_lines": overfull_lines,
        "underfull_lines": underfull_lines,
    }


def _measure_region_ink(
    grayscale: Image.Image,
    *,
    bbox: tuple[int, int, int, int],
    threshold: int,
) -> dict[str, Any]:
    x0, y0, x1, y1 = bbox
    if x1 <= x0 or y1 <= y0:
        return {"ink_pixels": 0, "total_pixels": 0, "ink_ratio": 0.0}
    crop = grayscale.crop(bbox)
    total_pixels = crop.width * crop.height
    ink_pixels = sum(1 for value in crop.tobytes() if value < threshold)
    ink_ratio = ink_pixels / total_pixels if total_pixels else 0.0
    return {
        "ink_pixels": ink_pixels,
        "total_pixels": total_pixels,
        "ink_ratio": ink_ratio,
    }


def _tex_warning_line_number(line: str) -> int | None:
    match = re.search(r":(?P<line>\d+):\s*(?:Overfull|Underfull)\s+\\[hv]box", line)
    if match is None:
        return None
    return int(match.group("line"))
