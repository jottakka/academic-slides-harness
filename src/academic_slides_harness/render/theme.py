from __future__ import annotations

import json
from importlib import resources
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

JsonScalar = str | int | float | bool | None


class ThemePresetError(ValueError):
    def __init__(self, kind: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.details = details or {}


class _StrictThemeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ThemeLogo(_StrictThemeModel):
    path: str | None = None
    placement: str = Field(min_length=1)
    max_width: float = Field(gt=0, le=1)
    max_height: float = Field(gt=0, le=1)

    @field_validator("path")
    @classmethod
    def _require_non_blank_path(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("logo path must be null or a non-blank path")
        return value


class ThemePreset(_StrictThemeModel):
    name: str = Field(min_length=1)
    version: int = Field(strict=True, ge=1)
    description: str = Field(min_length=1)
    colors: dict[str, str] = Field(min_length=1)
    fonts: dict[str, str] = Field(min_length=1)
    logo: ThemeLogo
    beamer: dict[str, JsonScalar] = Field(min_length=1)
    layout_defaults: dict[str, JsonScalar] = Field(min_length=1)

    @field_validator("name", "description")
    @classmethod
    def _require_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("colors", "fonts")
    @classmethod
    def _require_non_blank_mapping_values(cls, value: dict[str, str]) -> dict[str, str]:
        invalid_keys = [key for key in value if not key.strip()]
        invalid_values = [key for key, item in value.items() if not item.strip()]
        if invalid_keys:
            raise ValueError(f"blank keys are not allowed: {invalid_keys}")
        if invalid_values:
            raise ValueError(f"blank values are not allowed for: {invalid_values}")
        return value


def load_theme_preset(name_or_path: str | Path) -> dict[str, Any]:
    preset_path = _resolve_preset_path(name_or_path)
    raw_data = _read_json_object(preset_path)
    preset = _validate_theme_preset(raw_data, preset_path=preset_path)
    data = preset.model_dump(mode="json")
    data["logo"] = _resolve_logo(data["logo"], preset_path=preset_path)
    return data


def _resolve_preset_path(name_or_path: str | Path) -> Path:
    candidate = Path(name_or_path)
    if candidate.is_file():
        return candidate.resolve()
    if candidate.suffix == ".json" or candidate.parent != Path("."):
        raise ThemePresetError(
            "missing_preset",
            f"Theme preset file does not exist: {candidate}",
            details={"path": str(candidate)},
        )

    named_path = theme_preset_path(candidate.name)
    if named_path.is_file():
        return named_path.resolve()
    raise ThemePresetError(
        "missing_preset",
        f"Theme preset named {candidate.name!r} does not exist at {named_path}",
        details={"name": candidate.name, "path": str(named_path)},
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ThemePresetError(
            "invalid_json",
            f"Theme preset JSON is invalid at {path}: {exc.msg}",
            details={"path": str(path), "line": exc.lineno, "column": exc.colno},
        ) from exc

    if not isinstance(data, dict):
        raise ThemePresetError(
            "invalid_schema",
            f"Theme preset root must be a JSON object at {path}",
            details={"path": str(path)},
        )
    return data


def _validate_theme_preset(data: dict[str, Any], *, preset_path: Path) -> ThemePreset:
    try:
        return ThemePreset.model_validate(data)
    except ValidationError as exc:
        locations = ["/".join(str(part) for part in error["loc"]) for error in exc.errors()]
        raise ThemePresetError(
            "invalid_schema",
            f"Theme preset schema is invalid at {preset_path}: {', '.join(locations)}",
            details={"path": str(preset_path), "errors": _json_safe_validation_errors(exc)},
        ) from exc


def _resolve_logo(logo: dict[str, Any], *, preset_path: Path) -> dict[str, Any]:
    logo_data = dict(logo)
    if logo_data["path"] is None:
        return logo_data

    logo_path = Path(logo_data["path"]).expanduser()
    if not logo_path.is_absolute():
        logo_path = preset_path.parent / logo_path
    resolved = logo_path.resolve()
    if not resolved.is_file():
        raise ThemePresetError(
            "missing_logo",
            (
                f"Theme preset {preset_path} references missing logo "
                f"{logo_data['path']!r} resolved to {resolved}"
            ),
            details={
                "preset_path": str(preset_path),
                "logo": logo_data["path"],
                "resolved_logo": str(resolved),
            },
        )
    logo_data["path"] = str(resolved)
    return logo_data


def _theme_preset_dir() -> Path:
    return Path(resources.files("academic_slides_harness").joinpath("templates", "themes"))


def theme_preset_path(name: str) -> Path:
    return (_theme_preset_dir() / f"{name}.json").resolve()


def _json_safe_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    safe_errors: list[dict[str, Any]] = []
    for error in exc.errors(include_url=False):
        safe_error = dict(error)
        ctx = safe_error.get("ctx")
        if isinstance(ctx, dict):
            safe_error["ctx"] = {key: str(value) for key, value in ctx.items()}
        safe_errors.append(safe_error)
    return safe_errors
