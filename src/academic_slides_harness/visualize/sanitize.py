from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from academic_slides_harness.core.models import sha256_file

MIN_VISUAL_WIDTH = 16
MIN_VISUAL_HEIGHT = 16


@dataclass(frozen=True)
class VisualAssetError(Exception):
    kind: str
    message: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class SanitizedVisualAsset:
    source_path: Path
    path: Path
    width: int
    height: int
    format: str
    mode: str
    sha256: str
    source_sha256: str
    converted: bool

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "mode": self.mode,
            "sha256": self.sha256,
            "source_sha256": self.source_sha256,
            "converted": self.converted,
        }


def sanitize_visual_asset(
    *,
    source_path: Path,
    output_dir: Path,
    min_width: int = MIN_VISUAL_WIDTH,
    min_height: int = MIN_VISUAL_HEIGHT,
    filename_stem: str | None = None,
) -> SanitizedVisualAsset:
    resolved_source = source_path.resolve()
    if not resolved_source.is_file():
        raise VisualAssetError(
            kind="missing_visual_artifact",
            message=f"Visual artifact not found: {source_path}",
            details={"artifact_path": str(resolved_source)},
        )

    try:
        with Image.open(resolved_source) as image:
            image.load()
            width, height = image.size
            source_format = (image.format or "").upper()
            source_mode = image.mode
            has_alpha = "A" in image.getbands() or image.info.get("transparency") is not None
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise VisualAssetError(
            kind="invalid_visual_artifact",
            message=f"Visual artifact is not a readable image: {resolved_source}",
            details={
                "artifact_path": str(resolved_source),
                "exception_type": exc.__class__.__name__,
            },
        ) from exc

    if width < min_width or height < min_height:
        raise VisualAssetError(
            kind="image_too_small",
            message=(
                f"Visual artifact is too small: {width}x{height}; "
                f"minimum is {min_width}x{min_height}."
            ),
            details={
                "artifact_path": str(resolved_source),
                "width": width,
                "height": height,
                "min_width": min_width,
                "min_height": min_height,
            },
        )

    source_sha256 = sha256_file(resolved_source)
    target_mode = "RGBA" if has_alpha else "RGB"
    source_suffix = resolved_source.suffix.lower()
    keep_original = (
        source_format in {"PNG", "JPEG"}
        and source_mode == target_mode
        and source_suffix in {".png", ".jpg", ".jpeg"}
    )
    target_format = _target_format(source_format)
    suffix = source_suffix if keep_original else _target_suffix(target_format)
    target_stem = filename_stem or resolved_source.stem
    target_path = output_dir / f"{source_sha256[:12]}-{target_stem}{suffix}"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if target_path.exists() and not target_path.is_file():
            raise OSError(f"Sanitized visual target is not a file: {target_path}")
        if not target_path.exists():
            if keep_original:
                shutil.copy2(resolved_source, target_path)
            else:
                _write_normalized_image(
                    source_path=resolved_source,
                    output_path=target_path,
                    mode=target_mode,
                    format=target_format,
                )
    except OSError as exc:
        raise VisualAssetError(
            kind="asset_copy_failed",
            message=str(exc),
            details={"source_path": str(resolved_source), "deck_path": str(target_path)},
        ) from exc

    return SanitizedVisualAsset(
        source_path=resolved_source,
        path=target_path.resolve(),
        width=width,
        height=height,
        format=source_format if keep_original else target_format,
        mode=target_mode,
        sha256=sha256_file(target_path),
        source_sha256=source_sha256,
        converted=not keep_original,
    )


def _target_format(source_format: str) -> str:
    if source_format == "JPEG":
        return "JPEG"
    return "PNG"


def _target_suffix(format: str) -> str:
    if format == "JPEG":
        return ".jpg"
    return ".png"


def _write_normalized_image(
    *,
    source_path: Path,
    output_path: Path,
    mode: str,
    format: str,
) -> None:
    with Image.open(source_path) as image:
        normalized = image.convert(mode)
        normalized.save(output_path, format=format)
