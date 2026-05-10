from __future__ import annotations

import json

import pytest

from academic_slides_harness.render.theme import ThemePresetError, load_theme_preset


def test_load_default_theme_preset_by_name_returns_json_friendly_data() -> None:
    preset = load_theme_preset("default_visual_academic")

    assert preset["name"] == "default_visual_academic"
    assert preset["version"] == 1
    assert preset["logo"]["path"] is None
    assert preset["logo"]["placement"] == "top_right"
    assert preset["colors"]["primary"].startswith("#")
    assert preset["fonts"]["body"]
    assert preset["beamer"]["aspect_ratio"] == "169"
    json.dumps(preset)


def test_load_theme_preset_rejects_invalid_json(tmp_path) -> None:
    preset_path = tmp_path / "broken.json"
    preset_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ThemePresetError) as exc_info:
        load_theme_preset(preset_path)

    assert exc_info.value.kind == "invalid_json"
    assert str(preset_path) in str(exc_info.value)


def test_load_theme_preset_rejects_missing_required_schema_field(tmp_path) -> None:
    preset_path = tmp_path / "missing-colors.json"
    preset_path.write_text(
        json.dumps(
            {
                "name": "missing_colors",
                "version": 1,
                "description": "Invalid preset without required colors.",
                "fonts": {"heading": "TeX Gyre Heros", "body": "TeX Gyre Pagella"},
                "logo": {
                    "path": None,
                    "placement": "top_right",
                    "max_width": 0.16,
                    "max_height": 0.08,
                },
                "beamer": {"theme": "Boadilla", "aspect_ratio": "169"},
                "layout_defaults": {"visual_density": "standard"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ThemePresetError) as exc_info:
        load_theme_preset(preset_path)

    assert exc_info.value.kind == "invalid_schema"
    assert "colors" in str(exc_info.value)
    json.dumps(exc_info.value.details)


def test_load_theme_preset_rejects_missing_logo_file(tmp_path) -> None:
    preset_path = tmp_path / "missing-logo.json"
    preset_path.write_text(
        json.dumps(
            {
                "name": "missing_logo",
                "version": 1,
                "description": "Invalid preset with unresolved logo path.",
                "colors": {"primary": "#1F4E79", "background": "#FFFFFF"},
                "fonts": {"heading": "TeX Gyre Heros", "body": "TeX Gyre Pagella"},
                "logo": {
                    "path": "assets/missing-logo.png",
                    "placement": "top_right",
                    "max_width": 0.16,
                    "max_height": 0.08,
                },
                "beamer": {"theme": "Boadilla", "aspect_ratio": "169"},
                "layout_defaults": {"visual_density": "standard"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ThemePresetError) as exc_info:
        load_theme_preset(preset_path)

    assert exc_info.value.kind == "missing_logo"
    assert "assets/missing-logo.png" in str(exc_info.value)


def test_load_theme_preset_accepts_absolute_path_and_resolves_existing_logo(tmp_path) -> None:
    logo_dir = tmp_path / "assets"
    logo_dir.mkdir()
    logo_path = logo_dir / "logo.png"
    logo_path.write_bytes(b"not a real png but exists")
    preset_path = tmp_path / "with-logo.json"
    preset_path.write_text(
        json.dumps(
            {
                "name": "with_logo",
                "version": 1,
                "description": "Valid preset with a resolvable logo.",
                "colors": {"primary": "#1F4E79", "background": "#FFFFFF"},
                "fonts": {"heading": "TeX Gyre Heros", "body": "TeX Gyre Pagella"},
                "logo": {
                    "path": "assets/logo.png",
                    "placement": "top_right",
                    "max_width": 0.16,
                    "max_height": 0.08,
                },
                "beamer": {"theme": "Boadilla", "aspect_ratio": "169"},
                "layout_defaults": {"visual_density": "standard"},
            }
        ),
        encoding="utf-8",
    )

    preset = load_theme_preset(preset_path.resolve())

    assert preset["name"] == "with_logo"
    assert preset["logo"]["path"] == str(logo_path.resolve())
