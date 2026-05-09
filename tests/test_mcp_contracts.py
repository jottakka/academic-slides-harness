from pathlib import Path

import fitz

from academic_slides_harness.mcp.server import (
    MCP_TOOL_NAMES,
    build_app,
    create_run,
    ingest_source,
    list_visual_artifacts,
    render_beamer,
    render_zoom_crop,
)


def test_mcp_tool_registry_contains_initial_contract() -> None:
    assert {
        "compile_rendered_beamer",
        "create_run",
        "ingest_source",
        "list_visual_artifacts",
        "plan_deck",
        "render_beamer",
        "render_slide_preview",
        "render_source_preview",
        "render_zoom_crop",
        "validate_run",
    } == MCP_TOOL_NAMES


def test_build_app_returns_arcade_app_with_expected_name() -> None:
    app = build_app()

    assert app.name == "academic_slides_harness"


def test_create_run_returns_structured_content(tmp_path: Path) -> None:
    result = create_run(base_dir=tmp_path, title="Compact Operators")

    assert result.ok is True
    assert Path(result.structured_content["run_dir"]).exists()
    assert Path(result.structured_content["manifest_path"]).exists()
    assert result.structured_content["state"] == "created"


def test_build_app_exposes_every_registered_tool_over_stdio_contract() -> None:
    app = build_app()
    tool_names = {
        f"{tool_name.toolkit_name}_{tool_name.name}" for tool_name in app._catalog.get_tool_names()
    }

    expected = {
        "AcademicSlidesHarness_CompileRenderedBeamer",
        "AcademicSlidesHarness_CreateRun",
        "AcademicSlidesHarness_IngestSource",
        "AcademicSlidesHarness_ListVisualArtifacts",
        "AcademicSlidesHarness_PlanDeck",
        "AcademicSlidesHarness_RenderBeamer",
        "AcademicSlidesHarness_RenderSlidePreview",
        "AcademicSlidesHarness_RenderSourcePreview",
        "AcademicSlidesHarness_RenderZoomCrop",
        "AcademicSlidesHarness_ValidateRun",
    }
    assert tool_names == expected


def test_ingest_source_returns_typed_error_for_missing_pdf(tmp_path: Path) -> None:
    result = ingest_source(source_path=str(tmp_path / "missing.pdf"))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_render_beamer_returns_tex_hash(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Hashable Deck",
        slides=[{"title": "One", "bullets": ["A"]}],
    )

    assert result.ok is True
    assert Path(result.structured_content["deck_tex"]).exists()
    assert result.structured_content["sha256"]


def test_render_beamer_returns_typed_error_for_bad_slide_shape(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Bad Deck",
        slides=[{"title": "Missing bullets"}],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_slide"


def test_list_visual_artifacts_returns_dimensions_and_hash(tmp_path: Path) -> None:
    image_path = tmp_path / "artifact.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 8), False)
    pixmap.clear_with(255)
    pixmap.save(image_path)

    result = list_visual_artifacts(screenshots_dir=str(tmp_path))

    artifact = result.structured_content["artifacts"][0]
    assert artifact["path"] == str(image_path.resolve())
    assert artifact["width"] == 12
    assert artifact["height"] == 8
    assert artifact["sha256"]


def test_render_zoom_crop_returns_typed_error_for_invalid_target(tmp_path: Path) -> None:
    result = render_zoom_crop(
        pdf_path=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        target="bad_target",
        page=1,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_target"
