import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_mcp_server_exposes_tools_over_stdio(tmp_path: Path) -> None:
    server_entrypoint = Path(__file__).resolve().parents[1] / "server.py"
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(server_entrypoint), "stdio"],
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        response = await session.list_tools()
        result = await session.call_tool(
            "AcademicSlidesHarness_CreateRun",
            {"base_dir": str(tmp_path), "title": "Stdio Smoke"},
        )

    tool_names = {tool.name for tool in response.tools}
    assert "AcademicSlidesHarness_CreateRun" in tool_names
    assert "AcademicSlidesHarness_CompileRenderedBeamer" in tool_names
    assert "AcademicSlidesHarness_RenderZoomCrop" in tool_names
    assert "AcademicSlidesHarness_ListVisualArtifacts" in tool_names
    assert not result.isError
    assert (tmp_path / "stdio-smoke").exists()
