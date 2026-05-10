import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

EXPECTED_TOOL_NAMES = {
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


@dataclass(frozen=True)
class StdioSmoke:
    tool_names: set[str]
    created_run_dir: Path
    created_manifest_path: Path


@pytest.mark.arcade_live
@pytest.mark.asyncio
async def test_local_arcade_mcp_stdio_exposes_and_calls_harness_tools(tmp_path: Path) -> None:
    if importlib.util.find_spec("arcade_mcp_server") is None:
        pytest.skip("Arcade MCP server runtime is not available")

    smoke = await _run_local_stdio_smoke(tmp_path)

    assert smoke.tool_names == EXPECTED_TOOL_NAMES
    assert smoke.created_run_dir == tmp_path / "arcade-live-stdio-smoke"
    assert smoke.created_manifest_path == smoke.created_run_dir / "manifest.json"
    assert smoke.created_run_dir.is_dir()
    assert smoke.created_manifest_path.is_file()


async def _run_local_stdio_smoke(tmp_path: Path) -> StdioSmoke:
    mcp_client = pytest.importorskip("mcp", reason="MCP Python client is not available")
    mcp_stdio = pytest.importorskip("mcp.client.stdio", reason="MCP stdio client is not available")
    server_entrypoint = Path(__file__).resolve().parents[1] / "server.py"
    server = mcp_stdio.StdioServerParameters(
        command=sys.executable,
        args=[str(server_entrypoint), "stdio"],
    )

    async with (
        mcp_stdio.stdio_client(server) as (read_stream, write_stream),
        mcp_client.ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools_response = await session.list_tools()
        create_run_result = await session.call_tool(
            "AcademicSlidesHarness_CreateRun",
            {"base_dir": str(tmp_path), "title": "Arcade Live Stdio Smoke"},
        )

    assert not create_run_result.isError
    created_run_dir = tmp_path / "arcade-live-stdio-smoke"
    return StdioSmoke(
        tool_names={tool.name for tool in tools_response.tools},
        created_run_dir=created_run_dir,
        created_manifest_path=created_run_dir / "manifest.json",
    )
