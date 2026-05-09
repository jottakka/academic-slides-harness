from pathlib import Path

import pytest
from pydantic import ValidationError

from academic_slides_harness.core.models import (
    RunManifest,
    ScreenshotArtifact,
    SourceDocument,
    ToolResult,
)


def test_source_document_uses_strict_validation() -> None:
    with pytest.raises(ValidationError):
        SourceDocument(path=Path("paper.pdf"), kind="pdf", pages="12")


def test_run_manifest_records_absolute_run_directory(tmp_path: Path) -> None:
    manifest = RunManifest.create(run_dir=tmp_path, title="Linear Algebra")

    assert manifest.run_dir == tmp_path.resolve()
    assert manifest.title == "Linear Algebra"
    assert manifest.state == "created"


def test_screenshot_artifact_exposes_structured_content(tmp_path: Path) -> None:
    path = tmp_path / "slide-001.png"
    path.write_bytes(b"png-bytes")

    artifact = ScreenshotArtifact.from_file(
        path=path,
        target="deck_pdf",
        page=1,
        width=320,
        height=240,
        dpi=144,
        scale=2.0,
        zoom=1.5,
    )

    content = artifact.to_structured_content()
    assert content["path"] == str(path.resolve())
    assert content["sha256"]
    assert content["width"] == 320
    assert content["resolution"]["dpi"] == 144
    assert content["resolution"]["scale"] == 2.0
    assert content["zoom"] == 1.5


def test_tool_result_error_shape_is_machine_readable() -> None:
    result = ToolResult.error(kind="missing_input", message="source_path is required")

    assert result.ok is False
    assert result.is_error is True
    assert result.structured_content["error"]["kind"] == "missing_input"
    assert "source_path" in result.content_text
