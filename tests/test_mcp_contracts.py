from pathlib import Path

from academic_slides_harness.mcp.server import MCP_TOOL_NAMES, build_app, create_run


def test_mcp_tool_registry_contains_initial_contract() -> None:
    assert {
        "create_run",
        "ingest_source",
        "plan_deck",
        "render_beamer",
        "validate_run",
        "render_slide_preview",
        "render_source_preview",
        "render_zoom_crop",
        "list_visual_artifacts",
    }.issubset(MCP_TOOL_NAMES)


def test_build_app_returns_arcade_app_with_expected_name() -> None:
    app = build_app()

    assert app.name == "academic_slides_harness"


def test_create_run_returns_structured_content(tmp_path: Path) -> None:
    result = create_run(base_dir=tmp_path, title="Compact Operators")

    assert result.ok is True
    assert Path(result.structured_content["run_dir"]).exists()
    assert result.structured_content["state"] == "created"
