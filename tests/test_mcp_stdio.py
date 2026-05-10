import sys
from pathlib import Path

import fitz
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_mcp_server_exposes_tools_over_stdio(tmp_path: Path) -> None:
    server_entrypoint = Path(__file__).resolve().parents[1] / "server.py"
    source_pdf = _make_pdf(tmp_path / "source.pdf")
    visual_path = _make_png(tmp_path / "source.png")
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
        extract_result = await session.call_tool(
            "AcademicSlidesHarness_ExtractSourcePages",
            {"source_pdf": str(source_pdf), "pages": "1", "max_chars_per_page": 200},
        )
        rich_result = await session.call_tool(
            "AcademicSlidesHarness_RenderRichBeamer",
            {
                "output_dir": str(tmp_path / "rich-rendered"),
                "title": "Rich Stdio Deck",
                "slides": [
                    {
                        "title": "Visual Evidence",
                        "layout": "figure_explanation",
                        "learning_goal": "Use a real image in the generated slide.",
                        "blocks": [
                            {"type": "visual", "artifact_path": str(visual_path)},
                            {"type": "claim", "text": "The image is rendered as evidence."},
                            {"type": "source_citation", "source_page": 1},
                        ],
                    }
                ],
            },
        )

    tool_names = {tool.name for tool in response.tools}
    assert tool_names == {
        "AcademicSlidesHarness_CompileRenderedBeamer",
        "AcademicSlidesHarness_CreateRun",
        "AcademicSlidesHarness_ExtractSourcePages",
        "AcademicSlidesHarness_IngestSource",
        "AcademicSlidesHarness_ListVisualArtifacts",
        "AcademicSlidesHarness_PlanDeck",
        "AcademicSlidesHarness_RenderBeamer",
        "AcademicSlidesHarness_RenderRichBeamer",
        "AcademicSlidesHarness_RenderSlidePreview",
        "AcademicSlidesHarness_RenderSourcePreview",
        "AcademicSlidesHarness_RenderZoomCrop",
        "AcademicSlidesHarness_ValidateRun",
    }
    assert not result.isError
    assert not extract_result.isError
    assert not rich_result.isError
    assert "Stdio extracted source text" in str(extract_result.content)
    assert (tmp_path / "rich-rendered" / "deck.tex").exists()
    assert (tmp_path / "stdio-smoke").exists()


@pytest.mark.asyncio
async def test_mcp_server_stdio_returns_utf8_when_parent_codepage_is_not_utf8(
    tmp_path: Path,
) -> None:
    server_entrypoint = Path(__file__).resolve().parents[1] / "server.py"
    text = "Alpha " + chr(0x2013) + " Beta " + chr(0x00A9)
    source_pdf = _make_pdf(tmp_path / "source.pdf", text=text)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(server_entrypoint), "stdio"],
        env={"PYTHONIOENCODING": "cp1252"},
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        extract_result = await session.call_tool(
            "AcademicSlidesHarness_ExtractSourcePages",
            {"source_pdf": str(source_pdf), "pages": "1", "max_chars_per_page": 200},
        )

    assert not extract_result.isError
    assert "Alpha" in str(extract_result.content)
    assert "Beta" in str(extract_result.content)


def _make_pdf(path: Path, *, text: str = "Stdio extracted source text") -> Path:
    doc = fitz.open()
    page = doc.new_page(width=200, height=120)
    page.insert_text((36, 60), text, fontsize=12)
    doc.save(path)
    doc.close()
    return path


def _make_png(path: Path) -> Path:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 24, 16), False)
    pixmap.clear_with(180)
    pixmap.save(path)
    return path
