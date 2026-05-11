from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageStat

VisualQualityContext = Literal[
    "generic",
    "source_preview",
    "source_crop",
    "deck_preview",
    "deck_crop",
]


@dataclass(frozen=True)
class VisualQualityWarning:
    kind: str
    severity: Literal["warning", "error"]
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
class VisualQualityReport:
    ok: bool
    metrics: dict[str, Any]
    warnings: tuple[VisualQualityWarning, ...]

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "metrics": self.metrics,
            "warnings": [warning.to_structured_content() for warning in self.warnings],
        }


def assess_visual_quality(
    image_path: Path,
    *,
    context: VisualQualityContext = "generic",
) -> VisualQualityReport:
    with Image.open(image_path) as image:
        gray = image.convert("L")
        metrics = _image_metrics(gray)

    warnings = _quality_warnings(metrics=metrics, context=context)
    return VisualQualityReport(
        ok=not any(warning.severity == "error" for warning in warnings),
        metrics=metrics,
        warnings=tuple(warnings),
    )


def _image_metrics(gray: Image.Image) -> dict[str, Any]:
    width, height = gray.size
    pixels = gray.tobytes()
    total_pixels = width * height
    ink_pixels = sum(pixel < 245 for pixel in pixels)
    dark_pixels = sum(pixel < 190 for pixel in pixels)
    row_ink_ratios = _row_ink_ratios(pixels=pixels, width=width, height=height)
    active_rows = [ratio > 0.01 for ratio in row_ink_ratios]
    component_metrics = _component_metrics(gray)
    stat = ImageStat.Stat(gray)

    return {
        "width": width,
        "height": height,
        "aspect_ratio": width / height,
        "portrait_ratio": height / width,
        "ink_ratio": ink_pixels / total_pixels,
        "dark_ink_ratio": dark_pixels / total_pixels,
        "contrast_stddev": stat.stddev[0],
        "active_row_ratio": sum(active_rows) / height,
        "row_run_count": _count_runs(active_rows),
        "max_row_ink_ratio": max(row_ink_ratios) if row_ink_ratios else 0.0,
        **component_metrics,
    }


def _quality_warnings(
    *,
    metrics: dict[str, Any],
    context: VisualQualityContext,
) -> list[VisualQualityWarning]:
    warnings: list[VisualQualityWarning] = []
    if metrics["ink_ratio"] < 0.015:
        warnings.append(
            VisualQualityWarning(
                kind="low_visual_density",
                severity="warning",
                message="Artifact has very little visible content.",
                details={"ink_ratio": metrics["ink_ratio"]},
            )
        )
    if metrics["contrast_stddev"] < 8.0:
        warnings.append(
            VisualQualityWarning(
                kind="low_contrast",
                severity="warning",
                message="Artifact has low contrast and may be hard to read.",
                details={"contrast_stddev": metrics["contrast_stddev"]},
            )
        )
    if context == "source_preview" and metrics["portrait_ratio"] >= 1.25:
        warnings.append(
            VisualQualityWarning(
                kind="page_like_snapshot",
                severity="warning",
                message=(
                    "Artifact is a portrait page snapshot; use a focused crop for slide visuals."
                ),
                details={"portrait_ratio": metrics["portrait_ratio"]},
            )
        )
    if (
        context in {"generic", "source_preview", "source_crop"}
        and metrics["small_component_density_per_megapixel"] >= 1500
        and metrics["active_row_ratio"] >= 0.30
    ):
        warnings.append(
            VisualQualityWarning(
                kind="text_heavy_crop",
                severity="warning",
                message=(
                    "Artifact appears dominated by embedded text; crop tighter around the figure."
                ),
                details={
                    "small_component_density_per_megapixel": metrics[
                        "small_component_density_per_megapixel"
                    ],
                    "active_row_ratio": metrics["active_row_ratio"],
                },
            )
        )
    return warnings


def _row_ink_ratios(*, pixels: bytes, width: int, height: int) -> list[float]:
    ratios: list[float] = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        ratios.append(sum(pixel < 245 for pixel in row) / width)
    return ratios


def _component_metrics(gray: Image.Image) -> dict[str, Any]:
    analysis_image = _analysis_size_image(gray)
    width, height = analysis_image.size
    pixels = analysis_image.tobytes()
    visited = bytearray(width * height)
    components = 0
    small_components = 0
    large_components = 0

    for index, pixel in enumerate(pixels):
        if visited[index] or pixel >= 190:
            continue
        size = _mark_component(
            start_index=index,
            pixels=pixels,
            visited=visited,
            width=width,
            height=height,
        )
        components += 1
        if 3 <= size <= 180:
            small_components += 1
        if size > 1000:
            large_components += 1

    megapixels = (width * height) / 1_000_000
    return {
        "analysis_width": width,
        "analysis_height": height,
        "component_count": components,
        "small_component_count": small_components,
        "large_component_count": large_components,
        "small_component_density_per_megapixel": small_components / megapixels,
    }


def _analysis_size_image(gray: Image.Image) -> Image.Image:
    width, height = gray.size
    if width * height <= 500_000:
        return gray
    scale = (500_000 / (width * height)) ** 0.5
    resized = (max(1, int(width * scale)), max(1, int(height * scale)))
    return gray.resize(resized, Image.Resampling.BILINEAR)


def _mark_component(
    *,
    start_index: int,
    pixels: bytes,
    visited: bytearray,
    width: int,
    height: int,
) -> int:
    stack = [start_index]
    visited[start_index] = 1
    size = 0

    while stack:
        index = stack.pop()
        size += 1
        x = index % width
        y = index // width
        for next_y in range(max(0, y - 1), min(height, y + 2)):
            row_offset = next_y * width
            for next_x in range(max(0, x - 1), min(width, x + 2)):
                next_index = row_offset + next_x
                if visited[next_index] or pixels[next_index] >= 190:
                    continue
                visited[next_index] = 1
                stack.append(next_index)
    return size


def _count_runs(flags: list[bool]) -> int:
    runs = 0
    in_run = False
    for flag in flags:
        if flag and not in_run:
            runs += 1
            in_run = True
        elif not flag:
            in_run = False
    return runs
