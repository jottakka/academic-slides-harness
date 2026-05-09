from pathlib import Path
from typing import Annotated, Any

from arcade_mcp_server import MCPApp

from academic_slides_harness.core.models import RunManifest, ToolResult
from academic_slides_harness.ingest.pdf import inspect_pdf
from academic_slides_harness.llm.providers import NoLLMProvider
from academic_slides_harness.render.beamer import BeamerDeck, BeamerSlide, render_beamer_tex
from academic_slides_harness.render.tectonic import compile_tex_with_tectonic
from academic_slides_harness.visualize.options import CropBox, RenderOptions, parse_page_selection
from academic_slides_harness.visualize.preview import (
    render_pdf_pages,
)
from academic_slides_harness.visualize.preview import (
    render_zoom_crop as render_crop,
)

MCP_TOOL_NAMES = frozenset(
    {
        "create_run",
        "ingest_source",
        "plan_deck",
        "render_beamer",
        "validate_run",
        "render_slide_preview",
        "render_source_preview",
        "render_zoom_crop",
        "list_visual_artifacts",
    }
)


def create_run(
    *,
    base_dir: Annotated[str, "Directory where the run folder should be created."],
    title: Annotated[str, "Human-readable deck or source title for the run."],
) -> ToolResult:
    """Create a local academic slide generation run directory and manifest."""
    run_dir = Path(base_dir).resolve() / _slug(title)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "screenshots").mkdir(exist_ok=True)
    manifest = RunManifest.create(run_dir=run_dir, title=title)
    return ToolResult.success(
        message=f"Created run {manifest.run_id}",
        structured_content=manifest.to_structured_content(),
    )


def ingest_source(
    *,
    source_path: Annotated[str, "Absolute or relative path to the source PDF."],
) -> ToolResult:
    """Inspect a source PDF and return deterministic ingestion metadata."""
    if not Path(source_path).exists():
        return ToolResult.error(kind="missing_input", message=f"Source not found: {source_path}")
    source = inspect_pdf(Path(source_path))
    return ToolResult.success(
        message=f"Ingested {source.pages} pages",
        structured_content=source.model_dump(mode="json"),
    )


def plan_deck(
    *,
    title: Annotated[str, "Deck title."],
    excerpts: Annotated[list[str], "Ordered source excerpts to turn into slide drafts."],
    max_slides: Annotated[int, "Maximum number of slide drafts to produce."] = 8,
) -> ToolResult:
    """Create a deterministic slide plan from source excerpts."""
    plan = NoLLMProvider().plan_deck(title=title, excerpts=excerpts, max_slides=max_slides)
    return ToolResult.success(
        message=f"Planned {len(plan.slides)} slides",
        structured_content=plan.model_dump(mode="json"),
    )


def render_beamer(
    *,
    output_dir: Annotated[str, "Directory where deck.tex should be written."],
    title: Annotated[str, "Deck title."],
    slides: Annotated[list[dict[str, Any]], "Slide objects with title and bullets fields."],
) -> ToolResult:
    """Render a Beamer deck.tex file from structured slide data."""
    deck = BeamerDeck(
        title=title,
        slides=[
            BeamerSlide(title=str(slide["title"]), bullets=[str(item) for item in slide["bullets"]])
            for slide in slides
        ],
    )
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "deck.tex"
    tex_path.write_text(render_beamer_tex(deck), encoding="utf-8")
    return ToolResult.success(
        message="Rendered Beamer source",
        structured_content={"deck_tex": str(tex_path), "title": title},
    )


def validate_run(
    *,
    run_dir: Annotated[str, "Run directory to validate."],
) -> ToolResult:
    """Run lightweight deterministic validation checks for a run directory."""
    path = Path(run_dir).resolve()
    checks = {
        "run_dir_exists": path.exists(),
        "screenshots_dir_exists": (path / "screenshots").exists(),
    }
    return ToolResult.success(
        message="Validation completed",
        structured_content={"ok": all(checks.values()), "checks": checks},
    )


def render_source_preview(
    *,
    source_pdf: Annotated[str, "Path to the source PDF to preview."],
    output_dir: Annotated[str, "Directory where PNG previews should be written."],
    pages: Annotated[str, "One-based page selection, for example '1-3,5'."],
    resolution: Annotated[str, "Resolution preset: fast, review, or print."] = "review",
    dpi: Annotated[int, "Explicit DPI override; use 0 to keep the preset."] = 0,
    scale: Annotated[float, "Explicit render scale override; use 0 to derive from DPI."] = 0.0,
) -> ToolResult:
    """Render source PDF pages to PNG preview artifacts."""
    artifacts = render_pdf_pages(
        pdf_path=Path(source_pdf),
        output_dir=Path(output_dir),
        target="source_pdf",
        pages=parse_page_selection(pages),
        options=RenderOptions(
            resolution=resolution,
            dpi=dpi or None,
            scale=scale or None,
        ),
    )
    return ToolResult.success(
        message=f"Rendered {len(artifacts)} source previews",
        structured_content={
            "artifacts": [artifact.to_structured_content() for artifact in artifacts]
        },
    )


def render_slide_preview(
    *,
    deck_pdf: Annotated[str, "Path to the rendered deck PDF."],
    output_dir: Annotated[str, "Directory where PNG slide previews should be written."],
    slides: Annotated[str, "One-based slide selection, for example '1-3,5'."],
    resolution: Annotated[str, "Resolution preset: fast, review, or print."] = "review",
    dpi: Annotated[int, "Explicit DPI override; use 0 to keep the preset."] = 0,
    scale: Annotated[float, "Explicit render scale override; use 0 to derive from DPI."] = 0.0,
) -> ToolResult:
    """Render deck PDF slides to PNG preview artifacts."""
    artifacts = render_pdf_pages(
        pdf_path=Path(deck_pdf),
        output_dir=Path(output_dir),
        target="deck_pdf",
        pages=parse_page_selection(slides),
        options=RenderOptions(
            resolution=resolution,
            dpi=dpi or None,
            scale=scale or None,
        ),
    )
    return ToolResult.success(
        message=f"Rendered {len(artifacts)} slide previews",
        structured_content={
            "artifacts": [artifact.to_structured_content() for artifact in artifacts]
        },
    )


def render_zoom_crop(
    *,
    pdf_path: Annotated[str, "Path to the source or deck PDF."],
    output_dir: Annotated[str, "Directory where the zoom crop PNG should be written."],
    target: Annotated[str, "Visual target identifier: source_pdf or deck_pdf."],
    page: Annotated[int, "One-based page or slide number to crop."],
    crop: Annotated[dict, "Crop box with x, y, width, height, and optional normalized flag."],
    resolution: Annotated[str, "Resolution preset: fast, review, or print."] = "review",
    dpi: Annotated[int, "Explicit DPI override; use 0 to keep the preset."] = 0,
    scale: Annotated[float, "Explicit render scale override; use 0 to derive from DPI."] = 0.0,
    zoom: Annotated[float, "Zoom multiplier applied to the crop render."] = 2.0,
) -> ToolResult:
    """Render a zoomed crop from a source or deck PDF for visual QA."""
    if target not in {"source_pdf", "deck_pdf"}:
        return ToolResult.error(
            kind="invalid_target", message=f"Unsupported visual target: {target}"
        )
    artifact = render_crop(
        pdf_path=Path(pdf_path),
        output_dir=Path(output_dir),
        target=target,
        page=page,
        crop=CropBox(
            x=float(crop["x"]),
            y=float(crop["y"]),
            width=float(crop["width"]),
            height=float(crop["height"]),
            normalized=bool(crop.get("normalized", True)),
        ),
        options=RenderOptions(
            resolution=resolution,
            dpi=dpi or None,
            scale=scale or None,
            zoom=zoom,
        ),
    )
    return ToolResult.success(
        message="Rendered zoom crop",
        structured_content={"artifact": artifact.to_structured_content()},
    )


def list_visual_artifacts(
    *,
    screenshots_dir: Annotated[str, "Directory containing PNG visual artifacts."],
) -> ToolResult:
    """List PNG visual artifact paths in a screenshots directory."""
    directory = Path(screenshots_dir).resolve()
    artifacts = sorted(str(path) for path in directory.glob("*.png")) if directory.exists() else []
    return ToolResult.success(
        message=f"Found {len(artifacts)} visual artifacts",
        structured_content={"screenshots_dir": str(directory), "paths": artifacts},
    )


def compile_rendered_beamer(
    *,
    tex_path: Annotated[str, "Path to the Beamer .tex file."],
    output_dir: Annotated[str, "Directory where the compiled PDF should be written."],
) -> ToolResult:
    """Compile a rendered Beamer .tex file to PDF with Tectonic."""
    pdf_path = compile_tex_with_tectonic(tex_path=Path(tex_path), output_dir=Path(output_dir))
    return ToolResult.success(
        message="Compiled Beamer PDF",
        structured_content={"pdf_path": str(pdf_path.resolve())},
    )


def build_app() -> MCPApp:
    app = MCPApp(name="academic_slides_harness")
    for tool in [
        create_run,
        ingest_source,
        plan_deck,
        render_beamer,
        validate_run,
        render_slide_preview,
        render_source_preview,
        render_zoom_crop,
        list_visual_artifacts,
    ]:
        app.add_tool(tool)
    app.add_text_resource(
        "academic-slides://prompts/draft_academic_deck",
        text=_DRAFT_PROMPT,
        name="draft_academic_deck",
        description="Prompt for drafting an academic Beamer deck.",
    )
    app.add_text_resource(
        "academic-slides://prompts/review_slide_validation",
        text=_REVIEW_PROMPT,
        name="review_slide_validation",
        description="Prompt for reviewing deterministic slide validation artifacts.",
    )
    app.add_text_resource(
        "academic-slides://prompts/review_visual_artifacts",
        text=_VISUAL_REVIEW_PROMPT,
        name="review_visual_artifacts",
        description="Prompt for reviewing screenshot and crop artifacts.",
    )
    return app


def _slug(title: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in title).strip("-")


_DRAFT_PROMPT = "Draft a Beamer-first academic deck from ingested source artifacts."
_REVIEW_PROMPT = "Review slide validation artifacts and report only evidence-backed issues."
_VISUAL_REVIEW_PROMPT = (
    "Review screenshots, crops, dimensions, and hashes before judging visual quality."
)
