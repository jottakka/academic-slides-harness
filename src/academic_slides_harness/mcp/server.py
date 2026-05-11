import json
import re
import sys
from pathlib import Path
from typing import Annotated, Any

from arcade_mcp_server import MCPApp
from PIL import Image
from pydantic import ValidationError

from academic_slides_harness.core.models import RunManifest, ToolResult, sha256_file
from academic_slides_harness.ingest.pdf import extract_pdf_page_text, inspect_pdf
from academic_slides_harness.llm.providers import NoLLMProvider, discover_model_providers
from academic_slides_harness.render.beamer import (
    BeamerDeck,
    BeamerSlide,
    RichBeamerDeck,
    RichBeamerSlide,
    RichSlideBlock,
    render_beamer_tex,
    render_rich_beamer_tex,
)
from academic_slides_harness.render.layout_catalog import (
    LAYOUT_PATTERNS,
    layout_catalog_markdown,
    parse_layout_selection,
    render_layout_placeholder_images,
    rich_slide_schema_markdown,
)
from academic_slides_harness.render.tectonic import compile_tex_with_tectonic
from academic_slides_harness.render.theme import (
    ThemePresetError,
    list_available_theme_preset_names,
    load_theme_preset,
    theme_preset_path,
)
from academic_slides_harness.visualize.options import CropBox, RenderOptions, parse_page_selection
from academic_slides_harness.visualize.preview import (
    render_pdf_pages,
)
from academic_slides_harness.visualize.preview import (
    render_zoom_crop as render_crop,
)
from academic_slides_harness.visualize.quality import assess_visual_quality
from academic_slides_harness.visualize.sanitize import VisualAssetError, sanitize_visual_asset

MCP_TOOL_NAMES = frozenset(
    {
        "compile_rendered_beamer",
        "create_run",
        "extract_source_pages",
        "ingest_source",
        "list_model_providers",
        "list_theme_presets",
        "plan_deck",
        "render_beamer",
        "render_layout_placeholders",
        "render_rich_beamer",
        "validate_run",
        "render_slide_preview",
        "render_source_preview",
        "render_zoom_crop",
        "list_visual_artifacts",
    }
)

_STATIC_MCP_RESOURCE_URIS = frozenset(
    {
        "academic-slides://layouts/rich_slide_patterns",
        "academic-slides://prompts/draft_academic_deck",
        "academic-slides://prompts/draft_visual_academic_deck",
        "academic-slides://prompts/didactic_quality_rubric",
        "academic-slides://prompts/review_slide_validation",
        "academic-slides://prompts/review_visual_artifacts",
        "academic-slides://prompts/visual_quality_rubric",
        "academic-slides://schemas/rich_slide_plan",
    }
)
MCP_RESOURCE_URIS = _STATIC_MCP_RESOURCE_URIS | frozenset(
    f"academic-slides://themes/{name}" for name in list_available_theme_preset_names()
)

DEFAULT_THEME_PRESET_NAME = "default_visual_academic"
_FORBIDDEN_LATEX_COMMAND_RE = re.compile(
    r"\\(?:input|include|includegraphics|write|openout|read|catcode|def|gdef|edef|"
    r"newcommand|renewcommand|usepackage|documentclass)\b|\\(?:begin|end)\s*\{\s*document\s*\}",
    re.IGNORECASE,
)


def create_run(
    *,
    base_dir: Annotated[str, "Directory where the run folder should be created."],
    title: Annotated[str, "Human-readable deck or source title for the run."],
) -> ToolResult:
    """Create a local academic slide generation run directory and manifest."""
    base_path = Path(base_dir).resolve()
    if base_path.exists() and not base_path.is_dir():
        return ToolResult.error(
            kind="invalid_base_dir",
            message=f"Base path is not a directory: {base_path}",
            details={"base_dir": str(base_path)},
        )
    slug = _slug(title)
    if not slug:
        return ToolResult.error(
            kind="invalid_title",
            message="Run title must include at least one alphanumeric character.",
        )
    run_dir = base_path / slug
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "screenshots").mkdir(exist_ok=True)
    manifest = RunManifest.create(run_dir=run_dir, title=title)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    structured_content = manifest.to_structured_content()
    structured_content["manifest_path"] = str(manifest_path.resolve())
    return ToolResult.success(
        message=f"Created run {manifest.run_id}",
        structured_content=structured_content,
    )


def ingest_source(
    *,
    source_path: Annotated[str, "Absolute or relative path to the source PDF."],
) -> ToolResult:
    """Inspect a source PDF and return deterministic ingestion metadata."""
    if not Path(source_path).is_file():
        return ToolResult.error(kind="missing_input", message=f"Source not found: {source_path}")
    try:
        source = inspect_pdf(Path(source_path))
    except Exception as exc:
        return _exception_result(kind="ingest_failed", exc=exc)
    return ToolResult.success(
        message=f"Ingested {source.pages} pages",
        structured_content=source.model_dump(mode="json"),
    )


def extract_source_pages(
    *,
    source_pdf: Annotated[str, "Path to the source PDF to extract text from."],
    pages: Annotated[str, "One-based page selection, for example '1-3,5'."],
    max_chars_per_page: Annotated[
        int, "Maximum number of extracted text characters to return per page."
    ] = 2000,
) -> ToolResult:
    """Extract deterministic page text excerpts from a source PDF for deck planning."""
    try:
        selected_pages = parse_page_selection(pages)
    except ValueError as exc:
        return _exception_result(kind="invalid_page_selection", exc=exc)
    if max_chars_per_page < 1:
        return ToolResult.error(
            kind="invalid_options",
            message="max_chars_per_page must be a positive integer.",
            details={"max_chars_per_page": max_chars_per_page},
        )
    missing_input = _missing_file_result(path=source_pdf, label="Source PDF")
    if missing_input is not None:
        return missing_input
    try:
        structured_content = extract_pdf_page_text(
            Path(source_pdf),
            pages=selected_pages,
            max_chars_per_page=max_chars_per_page,
        )
    except ValueError as exc:
        return _exception_result(kind="invalid_page_selection", exc=exc)
    except Exception as exc:
        return _exception_result(kind="extract_failed", exc=exc)
    return ToolResult.success(
        message=f"Extracted text from {len(structured_content['pages'])} pages",
        structured_content=structured_content,
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


def list_model_providers(
    *,
    ollama_base_url: Annotated[
        str,
        "Ollama server base URL to probe. Defaults to the local Ollama API.",
    ] = "http://127.0.0.1:11434",
    timeout_seconds: Annotated[
        float,
        "Timeout in seconds for local provider probes.",
    ] = 1.0,
) -> ToolResult:
    """List redacted local and configured model-provider availability."""
    if timeout_seconds <= 0:
        return ToolResult.error(
            kind="invalid_options",
            message="timeout_seconds must be positive.",
            details={"timeout_seconds": timeout_seconds},
        )
    providers = discover_model_providers(
        ollama_base_url=ollama_base_url,
        timeout_seconds=timeout_seconds,
    )
    return ToolResult.success(
        message="Listed model provider availability",
        structured_content={"ok": True, "providers": providers},
    )


def render_beamer(
    *,
    output_dir: Annotated[str, "Directory where deck.tex should be written."],
    title: Annotated[str, "Deck title."],
    slides: Annotated[
        list[dict[str, Any]], "Slide objects with title and bullets fields, or body fields."
    ],
) -> ToolResult:
    """Render a Beamer deck.tex file from structured slide data."""
    if not isinstance(slides, list):
        return ToolResult.error(
            kind="invalid_slides",
            message="Slides must be a list of slide objects.",
            details={"actual_type": type(slides).__name__},
        )
    parsed_slides: list[BeamerSlide] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            return ToolResult.error(
                kind="invalid_slide",
                message=f"Slide {index} must be an object.",
                details={"slide_index": index, "actual_type": type(slide).__name__},
            )
        if "title" not in slide:
            return ToolResult.error(
                kind="invalid_slide",
                message=f"Slide {index} must include title.",
                details={"slide_index": index},
            )
        bullets = _slide_bullets(slide)
        if bullets is None:
            return ToolResult.error(
                kind="invalid_slide",
                message=f"Slide {index} must include bullets or body.",
                details={"slide_index": index},
            )
        parsed_slides.append(BeamerSlide(title=str(slide["title"]), bullets=bullets))
    deck = BeamerDeck(
        title=title,
        slides=parsed_slides,
    )
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "deck.tex"
    tex_path.write_text(render_beamer_tex(deck), encoding="utf-8")
    return ToolResult.success(
        message="Rendered Beamer source",
        structured_content={
            "deck_tex": str(tex_path),
            "title": title,
            "sha256": sha256_file(tex_path),
        },
    )


def render_rich_beamer(
    *,
    output_dir: Annotated[str, "Directory where deck.tex and copied visual assets are written."],
    title: Annotated[str, "Deck title."],
    slides: Annotated[
        list[dict[str, Any]],
        "Rich slide objects with layout, optional learning_goal, and typed blocks.",
    ],
) -> ToolResult:
    """Render a visually structured Beamer deck from a safe rich slide schema."""
    if not isinstance(slides, list):
        return ToolResult.error(
            kind="invalid_slides",
            message="Slides must be a list of rich slide objects.",
            details={"actual_type": type(slides).__name__},
        )
    out_dir = Path(output_dir).resolve()
    try:
        parsed_slides, assets = _parse_rich_slides(slides=slides, output_dir=out_dir)
    except RichSlideParseError as exc:
        return ToolResult.error(kind=exc.kind, message=exc.message, details=exc.details)
    except Exception as exc:
        return _exception_result(kind="render_failed", exc=exc)

    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "deck.tex"
    deck = RichBeamerDeck(title=title, slides=parsed_slides)
    tex_path.write_text(render_rich_beamer_tex(deck), encoding="utf-8")
    return ToolResult.success(
        message="Rendered rich Beamer source",
        structured_content={
            "deck_tex": str(tex_path),
            "title": title,
            "slide_count": len(parsed_slides),
            "layouts": [slide.layout for slide in parsed_slides],
            "assets": assets,
            "sha256": sha256_file(tex_path),
        },
    )


def render_layout_placeholders(
    *,
    output_dir: Annotated[str, "Directory where layout placeholder PNGs should be written."],
    layouts: Annotated[
        str,
        "Comma-separated rich layout names, or 'all'.",
    ] = "all",
    width: Annotated[int, "Placeholder PNG width in pixels. Minimum 640."] = 1280,
    height: Annotated[int, "Placeholder PNG height in pixels. Minimum 360."] = 720,
    overwrite: Annotated[bool, "Overwrite existing placeholder PNGs when true."] = False,
) -> ToolResult:
    """Render visual placeholder PNGs for supported rich Beamer layouts."""
    if width < 640 or height < 360:
        return ToolResult.error(
            kind="invalid_options",
            message="Placeholder dimensions must be at least 640x360.",
            details={"width": width, "height": height},
        )
    try:
        selected_layouts = parse_layout_selection(layouts)
        artifacts = render_layout_placeholder_images(
            output_dir=Path(output_dir).resolve(),
            layouts=selected_layouts,
            width=width,
            height=height,
            overwrite=overwrite,
        )
    except ValueError as exc:
        return ToolResult.error(
            kind="invalid_layout",
            message=str(exc),
            details={"layouts": layouts, "known_layouts": list(LAYOUT_PATTERNS)},
        )
    except FileExistsError as exc:
        return ToolResult.error(
            kind="artifact_exists",
            message=f"Placeholder already exists: {exc.filename or exc}",
            details={"path": str(exc.filename or exc), "overwrite": overwrite},
        )
    except OSError as exc:
        return _exception_result(kind="placeholder_render_failed", exc=exc)
    return ToolResult.success(
        message=f"Rendered {len(artifacts)} layout placeholders",
        structured_content={
            "output_dir": str(Path(output_dir).resolve()),
            "layouts": selected_layouts,
            "artifacts": artifacts,
        },
    )


def list_theme_presets() -> ToolResult:
    """List deterministic deck theme presets available to MCP agents."""
    try:
        presets = [_theme_preset_payload(name) for name in list_available_theme_preset_names()]
    except ThemePresetError as exc:
        return ToolResult.error(kind=exc.kind, message=str(exc), details=exc.details)
    except OSError as exc:
        return _exception_result(kind="theme_preset_failed", exc=exc)
    return ToolResult.success(
        message="Listed theme presets",
        structured_content={"presets": presets},
    )


def validate_run(
    *,
    run_dir: Annotated[str, "Run directory to validate."],
) -> ToolResult:
    """Run lightweight deterministic validation checks for a run directory."""
    path = Path(run_dir).resolve()
    manifest_path = path / "manifest.json"
    checks = {
        "run_dir_exists": path.exists(),
        "screenshots_dir_exists": (path / "screenshots").exists(),
        "manifest_exists": manifest_path.exists(),
    }
    if checks["manifest_exists"]:
        checks.update(_validate_manifest_file(manifest_path=manifest_path, run_dir=path))
    if not all(checks.values()):
        return ToolResult.error(
            kind="validation_failed",
            message="Required run validation checks failed.",
            details={"ok": False, "checks": checks},
        )
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
    overwrite: Annotated[
        bool, "Whether an existing PNG artifact at the target path may be overwritten."
    ] = False,
) -> ToolResult:
    """Render source PDF pages to PNG preview artifacts."""
    try:
        selected_pages = parse_page_selection(pages)
    except ValueError as exc:
        return _exception_result(kind="invalid_page_selection", exc=exc)
    try:
        render_options = _parse_render_options(resolution=resolution, dpi=dpi, scale=scale)
    except ValueError as exc:
        return _exception_result(kind="invalid_render_options", exc=exc)
    missing_input = _missing_file_result(path=source_pdf, label="Source PDF")
    if missing_input is not None:
        return missing_input
    try:
        artifacts = render_pdf_pages(
            pdf_path=Path(source_pdf),
            output_dir=Path(output_dir),
            target="source_pdf",
            pages=selected_pages,
            options=render_options,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        return _exception_result(kind="artifact_exists", exc=exc)
    except Exception as exc:
        return _exception_result(kind="preview_failed", exc=exc)
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
    overwrite: Annotated[
        bool, "Whether an existing PNG artifact at the target path may be overwritten."
    ] = False,
) -> ToolResult:
    """Render deck PDF slides to PNG preview artifacts."""
    try:
        selected_slides = parse_page_selection(slides)
    except ValueError as exc:
        return _exception_result(kind="invalid_page_selection", exc=exc)
    try:
        render_options = _parse_render_options(resolution=resolution, dpi=dpi, scale=scale)
    except ValueError as exc:
        return _exception_result(kind="invalid_render_options", exc=exc)
    missing_input = _missing_file_result(path=deck_pdf, label="Deck PDF")
    if missing_input is not None:
        return missing_input
    try:
        artifacts = render_pdf_pages(
            pdf_path=Path(deck_pdf),
            output_dir=Path(output_dir),
            target="deck_pdf",
            pages=selected_slides,
            options=render_options,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        return _exception_result(kind="artifact_exists", exc=exc)
    except Exception as exc:
        return _exception_result(kind="preview_failed", exc=exc)
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
    overwrite: Annotated[
        bool, "Whether an existing PNG artifact at the target path may be overwritten."
    ] = False,
) -> ToolResult:
    """Render a zoomed crop from a source or deck PDF for visual QA."""
    if target not in {"source_pdf", "deck_pdf"}:
        return ToolResult.error(
            kind="invalid_target", message=f"Unsupported visual target: {target}"
        )
    if page < 1:
        return ToolResult.error(
            kind="invalid_page_selection",
            message="Crop page must be a one-based positive page number.",
            details={"page": page},
        )
    try:
        crop_box = _parse_crop_box(crop)
    except ValueError as exc:
        return ToolResult.error(kind="invalid_crop", message=str(exc), details={"crop": crop})
    try:
        render_options = _parse_render_options(
            resolution=resolution,
            dpi=dpi,
            scale=scale,
            zoom=zoom,
        )
    except ValueError as exc:
        return _exception_result(kind="invalid_render_options", exc=exc)
    missing_input = _missing_file_result(path=pdf_path, label="PDF")
    if missing_input is not None:
        return missing_input
    try:
        artifact = render_crop(
            pdf_path=Path(pdf_path),
            output_dir=Path(output_dir),
            target=target,
            page=page,
            crop=crop_box,
            options=render_options,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        return _exception_result(kind="artifact_exists", exc=exc)
    except Exception as exc:
        return _exception_result(kind="crop_failed", exc=exc)
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
    if not directory.is_dir():
        return ToolResult.error(
            kind="missing_input",
            message=f"Screenshots directory not found: {directory}",
            details={"screenshots_dir": str(directory)},
        )
    png_paths = sorted(directory.glob("*.png"))
    artifacts = [_png_metadata(path) for path in png_paths]
    return ToolResult.success(
        message=f"Found {len(artifacts)} visual artifacts",
        structured_content={
            "screenshots_dir": str(directory),
            "paths": [artifact["path"] for artifact in artifacts],
            "artifacts": artifacts,
        },
    )


def compile_rendered_beamer(
    *,
    tex_path: Annotated[str, "Path to the Beamer .tex file."],
    output_dir: Annotated[str, "Directory where the compiled PDF should be written."],
) -> ToolResult:
    """Compile a rendered Beamer .tex file to PDF with Tectonic."""
    missing_input = _missing_file_result(path=tex_path, label="TeX file")
    if missing_input is not None:
        return missing_input
    try:
        pdf_path = compile_tex_with_tectonic(tex_path=Path(tex_path), output_dir=Path(output_dir))
    except TimeoutError as exc:
        return _exception_result(kind="compile_timeout", exc=exc)
    except Exception as exc:
        return _exception_result(kind="compile_failed", exc=exc)
    return ToolResult.success(
        message="Compiled Beamer PDF",
        structured_content={
            "pdf_path": str(pdf_path.resolve()),
            "sha256": sha256_file(pdf_path),
        },
    )


def build_app() -> MCPApp:
    app = MCPApp(name="academic_slides_harness")
    for tool in [
        create_run,
        extract_source_pages,
        ingest_source,
        list_model_providers,
        list_theme_presets,
        plan_deck,
        render_beamer,
        render_layout_placeholders,
        render_rich_beamer,
        validate_run,
        render_slide_preview,
        render_source_preview,
        render_zoom_crop,
        list_visual_artifacts,
        compile_rendered_beamer,
    ]:
        app.add_tool(tool)
    for uri, text, name, description in _TEXT_RESOURCES:
        app.add_text_resource(
            uri,
            text=text,
            name=name,
            description=description,
        )
    for preset_name in list_available_theme_preset_names():
        app.add_text_resource(
            f"academic-slides://themes/{preset_name}",
            text=_theme_preset_resource_text(preset_name),
            name=f"{preset_name}_theme",
            description=f"{preset_name} reusable visual academic deck theme preset.",
        )
    return app


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    transport = args[0] if args else "stdio"
    if transport not in {"stdio", "http"}:
        raise SystemExit(f"Unsupported transport '{transport}'. Use 'stdio' or 'http'.")
    build_app().run(transport=transport)


def _slug(title: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in title).strip("-")


class RichSlideParseError(ValueError):
    def __init__(
        self,
        *,
        kind: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.details = details or {}


def _parse_rich_slides(
    *,
    slides: list[dict[str, Any]],
    output_dir: Path,
) -> tuple[list[RichBeamerSlide], list[dict[str, Any]]]:
    parsed_slides: list[RichBeamerSlide] = []
    assets: list[dict[str, Any]] = []
    assets_dir = output_dir / "assets"
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} must be an object.",
                details={"slide_index": index, "actual_type": type(slide).__name__},
            )
        title = _required_str(slide, field="title", kind="invalid_slide", slide_index=index)
        layout = _required_str(slide, field="layout", kind="invalid_layout", slide_index=index)
        if layout not in LAYOUT_PATTERNS:
            raise RichSlideParseError(
                kind="invalid_layout",
                message=f"Slide {index} uses unsupported layout: {layout}",
                details={"slide_index": index, "layout": layout},
            )
        raw_blocks = slide.get("blocks")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} must include a non-empty blocks list.",
                details={"slide_index": index},
            )
        learning_goal = slide.get("learning_goal")
        if learning_goal is not None and not isinstance(learning_goal, str):
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} learning_goal must be a string when provided.",
                details={"slide_index": index, "actual_type": type(learning_goal).__name__},
            )
        _validate_rich_slide_text_limits(
            slide_index=index,
            title=title,
            layout=layout,
            learning_goal=learning_goal,
            raw_blocks=raw_blocks,
        )
        parsed_blocks = [
            _parse_rich_block(
                block=block,
                slide_index=index,
                block_index=block_index,
                layout=layout,
                assets_dir=assets_dir,
                assets=assets,
            )
            for block_index, block in enumerate(raw_blocks, start=1)
        ]
        if layout in {"hero_visual", "figure_explanation"} and not _has_block_type(
            parsed_blocks,
            "visual",
        ):
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} layout {layout} requires a visual block.",
                details={"slide_index": index, "layout": layout},
            )
        if layout == "equation_explanation" and not _has_block_type(
            parsed_blocks,
            "latex_equation",
        ):
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} layout {layout} requires a latex_equation block.",
                details={"slide_index": index, "layout": layout},
            )
        if layout == "table_explanation" and not _has_block_type(
            parsed_blocks,
            "latex_table",
        ):
            raise RichSlideParseError(
                kind="invalid_slide",
                message=f"Slide {index} layout {layout} requires a latex_table block.",
                details={"slide_index": index, "layout": layout},
            )
        parsed_slides.append(
            RichBeamerSlide(
                title=title,
                layout=layout,
                learning_goal=learning_goal,
                blocks=parsed_blocks,
            )
        )
    return parsed_slides, assets


def _validate_rich_slide_text_limits(
    *,
    slide_index: int,
    title: str,
    layout: str,
    learning_goal: str | None,
    raw_blocks: list[Any],
) -> None:
    limits = LAYOUT_PATTERNS[layout].suggested_text_limits
    _enforce_text_limit(
        slide_index=slide_index,
        layout=layout,
        field="title",
        value=title,
        max_chars=limits["title"],
    )
    if learning_goal is not None:
        _enforce_text_limit(
            slide_index=slide_index,
            layout=layout,
            field="learning_goal",
            value=learning_goal,
            max_chars=limits["learning_goal"],
        )
    for block_index, block in enumerate(raw_blocks, start=1):
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type in {"claim", "explanation"} and isinstance(block.get("text"), str):
            max_chars = limits.get(block_type)
            if max_chars is not None:
                _enforce_text_limit(
                    slide_index=slide_index,
                    layout=layout,
                    field="text",
                    value=block["text"],
                    max_chars=max_chars,
                    block_index=block_index,
                    block_type=block_type,
                )
        if block_type == "steps" and isinstance(block.get("items"), list):
            items = [item for item in block["items"] if isinstance(item, str)]
            max_steps = limits.get("max_steps")
            if max_steps is not None and len(items) > max_steps:
                raise RichSlideParseError(
                    kind="text_overflow_risk",
                    message=(
                        f"Slide {slide_index} has {len(items)} workflow steps; "
                        f"maximum is {max_steps}."
                    ),
                    details={
                        "slide_index": slide_index,
                        "layout": layout,
                        "block_index": block_index,
                        "block_type": "steps",
                        "field": "steps",
                        "item_count": len(items),
                        "max_items": max_steps,
                        "remediation": "Merge or remove low-value steps before rendering.",
                    },
                )
            max_step_chars = limits.get("step")
            if max_step_chars is not None:
                for item_index, item in enumerate(items, start=1):
                    _enforce_text_limit(
                        slide_index=slide_index,
                        layout=layout,
                        field="step",
                        value=item,
                        max_chars=max_step_chars,
                        block_index=block_index,
                        block_type="steps",
                        item_index=item_index,
                    )
        if block_type == "latex_equation" and isinstance(block.get("caption"), str):
            max_caption_chars = limits.get("caption")
            if max_caption_chars is not None:
                _enforce_text_limit(
                    slide_index=slide_index,
                    layout=layout,
                    field="caption",
                    value=block["caption"],
                    max_chars=max_caption_chars,
                    block_index=block_index,
                    block_type="latex_equation",
                )
        if block_type == "latex_table" and isinstance(block.get("caption"), str):
            max_caption_chars = limits.get("caption")
            if max_caption_chars is not None:
                _enforce_text_limit(
                    slide_index=slide_index,
                    layout=layout,
                    field="caption",
                    value=block["caption"],
                    max_chars=max_caption_chars,
                    block_index=block_index,
                    block_type="latex_table",
                )


def _enforce_text_limit(
    *,
    slide_index: int,
    layout: str,
    field: str,
    value: str,
    max_chars: int,
    block_index: int | None = None,
    block_type: str | None = None,
    item_index: int | None = None,
) -> None:
    char_count = len(value.strip())
    if char_count <= max_chars:
        return
    details: dict[str, Any] = {
        "slide_index": slide_index,
        "layout": layout,
        "field": field,
        "char_count": char_count,
        "max_chars": max_chars,
        "remediation": "Shorten this text or move detail into speaker notes/source context.",
    }
    if block_index is not None:
        details["block_index"] = block_index
    if block_type is not None:
        details["block_type"] = block_type
    if item_index is not None:
        details["item_index"] = item_index
    raise RichSlideParseError(
        kind="text_overflow_risk",
        message=(
            f"Slide {slide_index} {field} has {char_count} characters; "
            f"maximum for {layout} is {max_chars}."
        ),
        details=details,
    )


def _parse_rich_block(
    *,
    block: Any,
    slide_index: int,
    block_index: int,
    layout: str,
    assets_dir: Path,
    assets: list[dict[str, Any]],
) -> RichSlideBlock:
    if not isinstance(block, dict):
        raise RichSlideParseError(
            kind="invalid_block",
            message=f"Slide {slide_index} block {block_index} must be an object.",
            details={
                "slide_index": slide_index,
                "block_index": block_index,
                "actual_type": type(block).__name__,
            },
        )
    block_type = _required_str(
        block,
        field="type",
        kind="invalid_block",
        slide_index=slide_index,
        block_index=block_index,
    )
    if block_type == "visual":
        artifact_path = _required_str(
            block,
            field="artifact_path",
            kind="invalid_block",
            slide_index=slide_index,
            block_index=block_index,
        )
        allow_quality_warnings = block.get("allow_visual_quality_warnings", False)
        if not isinstance(allow_quality_warnings, bool):
            raise RichSlideParseError(
                kind="invalid_block",
                message="allow_visual_quality_warnings must be a boolean when provided.",
                details={
                    "slide_index": slide_index,
                    "block_index": block_index,
                    "field": "allow_visual_quality_warnings",
                    "actual_type": type(allow_quality_warnings).__name__,
                },
            )
        deck_asset_path, asset = _copy_visual_asset(
            Path(artifact_path),
            assets_dir=assets_dir,
            slide_index=slide_index,
            block_index=block_index,
            layout=layout,
            allow_visual_quality_warnings=allow_quality_warnings,
        )
        assets.append(asset)
        return RichSlideBlock(type="visual", artifact_path=deck_asset_path.as_posix())
    if block_type in {"claim", "explanation"}:
        text = _required_str(
            block,
            field="text",
            kind="invalid_block",
            slide_index=slide_index,
            block_index=block_index,
        )
        return RichSlideBlock(type=block_type, text=text)
    if block_type == "source_citation":
        source_page = block.get("source_page")
        if not isinstance(source_page, int) or source_page < 1:
            raise RichSlideParseError(
                kind="invalid_block",
                message="source_citation blocks require a positive integer source_page.",
                details={"slide_index": slide_index, "block_index": block_index},
            )
        return RichSlideBlock(type="source_citation", source_page=source_page)
    if block_type == "steps":
        items = block.get("items")
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise RichSlideParseError(
                kind="invalid_block",
                message="steps blocks require an items list of strings.",
                details={"slide_index": slide_index, "block_index": block_index},
            )
        return RichSlideBlock(type="steps", items=items)
    if block_type == "latex_equation":
        latex = _required_str(
            block,
            field="latex",
            kind="invalid_latex_equation",
            slide_index=slide_index,
            block_index=block_index,
        )
        _validate_latex_equation(
            latex=latex,
            slide_index=slide_index,
            block_index=block_index,
            layout=layout,
        )
        caption = block.get("caption")
        if caption is not None and not isinstance(caption, str):
            raise RichSlideParseError(
                kind="invalid_latex_equation",
                message="latex_equation caption must be a string when provided.",
                details={"slide_index": slide_index, "block_index": block_index},
            )
        return RichSlideBlock(
            type="latex_equation",
            latex=latex,
            caption=caption.strip() if isinstance(caption, str) and caption.strip() else None,
        )
    if block_type == "latex_table":
        headers = _required_str_list(
            block.get("headers"),
            field="headers",
            kind="invalid_latex_table",
            slide_index=slide_index,
            block_index=block_index,
        )
        _validate_latex_table_cells(
            cells=headers,
            field="headers",
            slide_index=slide_index,
            block_index=block_index,
        )
        rows = _required_table_rows(
            block.get("rows"),
            headers=headers,
            slide_index=slide_index,
            block_index=block_index,
            layout=layout,
        )
        caption = block.get("caption")
        if caption is not None and not isinstance(caption, str):
            raise RichSlideParseError(
                kind="invalid_latex_table",
                message="latex_table caption must be a string when provided.",
                details={"slide_index": slide_index, "block_index": block_index},
            )
        return RichSlideBlock(
            type="latex_table",
            headers=headers,
            rows=rows,
            caption=caption.strip() if isinstance(caption, str) and caption.strip() else None,
        )
    raise RichSlideParseError(
        kind="invalid_block",
        message=f"Unsupported rich slide block type: {block_type}",
        details={"slide_index": slide_index, "block_index": block_index, "type": block_type},
    )


def _has_block_type(blocks: list[RichSlideBlock], block_type: str) -> bool:
    return any(block.type == block_type for block in blocks)


def _validate_latex_equation(
    *,
    latex: str,
    slide_index: int,
    block_index: int,
    layout: str,
) -> None:
    limits = LAYOUT_PATTERNS[layout].suggested_text_limits
    max_chars = limits.get("latex", 520)
    _enforce_text_limit(
        slide_index=slide_index,
        layout=layout,
        field="latex",
        value=latex,
        max_chars=max_chars,
        block_index=block_index,
        block_type="latex_equation",
    )
    if _FORBIDDEN_LATEX_COMMAND_RE.search(latex):
        raise RichSlideParseError(
            kind="invalid_latex_equation",
            message="latex_equation contains a forbidden LaTeX command.",
            details={
                "slide_index": slide_index,
                "block_index": block_index,
                "field": "latex",
                "remediation": (
                    "Use only math expressions, not file, package, macro, or document commands."
                ),
            },
        )


def _required_str_list(
    value: Any,
    *,
    field: str,
    kind: str,
    slide_index: int,
    block_index: int,
) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise RichSlideParseError(
            kind=kind,
            message=f"{field} must be a non-empty list of strings.",
            details={"slide_index": slide_index, "block_index": block_index, "field": field},
        )
    items = [item.strip() for item in value]
    if any(not item for item in items):
        raise RichSlideParseError(
            kind=kind,
            message=f"{field} must not contain blank strings.",
            details={"slide_index": slide_index, "block_index": block_index, "field": field},
        )
    return items


def _validate_latex_table_cells(
    *,
    cells: list[str],
    field: str,
    slide_index: int,
    block_index: int,
) -> None:
    for item_index, cell in enumerate(cells, start=1):
        if _FORBIDDEN_LATEX_COMMAND_RE.search(cell):
            raise RichSlideParseError(
                kind="invalid_latex_table",
                message="latex_table contains a forbidden LaTeX command.",
                details={
                    "slide_index": slide_index,
                    "block_index": block_index,
                    "field": field,
                    "item_index": item_index,
                    "remediation": (
                        "Use only text or inline math expressions in table cells, "
                        "not file, package, macro, or document commands."
                    ),
                },
            )


def _required_table_rows(
    value: Any,
    *,
    headers: list[str],
    slide_index: int,
    block_index: int,
    layout: str,
) -> list[list[str]]:
    limits = LAYOUT_PATTERNS[layout].suggested_text_limits
    max_columns = limits.get("max_columns", 5)
    max_rows = limits.get("max_rows", 8)
    max_cell_chars = limits.get("table_cell", 42)
    if len(headers) > max_columns:
        raise RichSlideParseError(
            kind="invalid_latex_table",
            message=f"latex_table has {len(headers)} columns; maximum is {max_columns}.",
            details={
                "slide_index": slide_index,
                "block_index": block_index,
                "field": "headers",
                "column_count": len(headers),
                "max_columns": max_columns,
            },
        )
    if not isinstance(value, list) or not value:
        raise RichSlideParseError(
            kind="invalid_latex_table",
            message="latex_table rows must be a non-empty list of row lists.",
            details={"slide_index": slide_index, "block_index": block_index, "field": "rows"},
        )
    if len(value) > max_rows:
        raise RichSlideParseError(
            kind="invalid_latex_table",
            message=f"latex_table has {len(value)} rows; maximum is {max_rows}.",
            details={
                "slide_index": slide_index,
                "block_index": block_index,
                "field": "rows",
                "row_count": len(value),
                "max_rows": max_rows,
            },
        )
    rows: list[list[str]] = []
    for row_index, row in enumerate(value, start=1):
        if (
            not isinstance(row, list)
            or len(row) != len(headers)
            or not all(isinstance(cell, str) for cell in row)
        ):
            raise RichSlideParseError(
                kind="invalid_latex_table",
                message="latex_table row shape must match the headers.",
                details={
                    "slide_index": slide_index,
                    "block_index": block_index,
                    "field": "rows",
                    "row_index": row_index,
                    "expected_columns": len(headers),
                },
            )
        stripped_row = [cell.strip() for cell in row]
        for column_index, cell in enumerate(stripped_row, start=1):
            _validate_latex_table_cells(
                cells=[cell],
                field="rows",
                slide_index=slide_index,
                block_index=block_index,
            )
            if len(cell) > max_cell_chars:
                raise RichSlideParseError(
                    kind="text_overflow_risk",
                    message=(
                        f"Slide {slide_index} table cell has {len(cell)} characters; "
                        f"maximum for {layout} is {max_cell_chars}."
                    ),
                    details={
                        "slide_index": slide_index,
                        "layout": layout,
                        "block_index": block_index,
                        "block_type": "latex_table",
                        "field": "table_cell",
                        "row_index": row_index,
                        "column_index": column_index,
                        "char_count": len(cell),
                        "max_chars": max_cell_chars,
                        "remediation": "Shorten the cell or split the table across slides.",
                    },
                )
        rows.append(stripped_row)
    return rows


def _copy_visual_asset(
    source_path: Path,
    *,
    assets_dir: Path,
    slide_index: int,
    block_index: int,
    layout: str,
    allow_visual_quality_warnings: bool,
) -> tuple[Path, dict[str, Any]]:
    quality = _visual_quality_for_source(source_path)
    if quality is not None:
        _raise_for_visual_quality(
            quality=quality,
            source_path=source_path,
            slide_index=slide_index,
            block_index=block_index,
            layout=layout,
            allow_visual_quality_warnings=allow_visual_quality_warnings,
        )

    safe_stem = _slug(source_path.stem) or "visual"
    try:
        sanitized = sanitize_visual_asset(
            source_path=source_path,
            output_dir=assets_dir,
            filename_stem=safe_stem,
        )
    except VisualAssetError as exc:
        raise RichSlideParseError(
            kind=exc.kind,
            message=exc.message,
            details=exc.details,
        ) from exc

    if quality is None:
        quality = assess_visual_quality(sanitized.path, context="generic").to_structured_content()
        _raise_for_visual_quality(
            quality=quality,
            source_path=source_path,
            slide_index=slide_index,
            block_index=block_index,
            layout=layout,
            allow_visual_quality_warnings=allow_visual_quality_warnings,
        )

    hard_warning_kinds = _hard_visual_warning_kinds(quality=quality, layout=layout)
    asset = {
        **sanitized.to_structured_content(),
        "deck_path": str(sanitized.path),
        "quality": quality,
    }
    if allow_visual_quality_warnings and hard_warning_kinds:
        asset["quality_override"] = True
    return Path("assets") / sanitized.path.name, asset


def _visual_quality_for_source(source_path: Path) -> dict[str, Any] | None:
    sidecar_quality = _visual_quality_from_sidecar(source_path)
    if sidecar_quality is not None:
        return sidecar_quality
    if not source_path.is_file():
        return None
    try:
        return assess_visual_quality(source_path, context="generic").to_structured_content()
    except OSError:
        return None


def _visual_quality_from_sidecar(path: Path) -> dict[str, Any] | None:
    metadata = _visual_metadata_from_sidecar(path)
    if metadata is None:
        return None
    quality = metadata.get("quality")
    return quality if isinstance(quality, dict) else None


def _raise_for_visual_quality(
    *,
    quality: dict[str, Any],
    source_path: Path,
    slide_index: int,
    block_index: int,
    layout: str,
    allow_visual_quality_warnings: bool,
) -> None:
    hard_warning_kinds = _hard_visual_warning_kinds(quality=quality, layout=layout)
    if not hard_warning_kinds or allow_visual_quality_warnings:
        return
    raise RichSlideParseError(
        kind="visual_quality_failed",
        message=(
            f"Visual artifact failed rich deck quality gate: {', '.join(hard_warning_kinds)}."
        ),
        details={
            "slide_index": slide_index,
            "block_index": block_index,
            "layout": layout,
            "artifact_path": str(source_path.resolve()),
            "warning_kinds": hard_warning_kinds,
            "warnings": _quality_warnings(quality),
            "remediation": (
                "Use a focused crop around the figure, chart, equation, or evidence region; "
                "crop tighter when the artifact is dominated by body text."
            ),
        },
    )


def _hard_visual_warning_kinds(*, quality: dict[str, Any], layout: str) -> list[str]:
    warning_kinds = [warning["kind"] for warning in _quality_warnings(quality) if "kind" in warning]
    hard_kinds: list[str] = []
    if layout == "hero_visual" and "page_like_snapshot" in warning_kinds:
        hard_kinds.append("page_like_snapshot")
    if "text_heavy_crop" in warning_kinds:
        hard_kinds.append("text_heavy_crop")
    return hard_kinds


def _quality_warnings(quality: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = quality.get("warnings", [])
    if not isinstance(warnings, list):
        return []
    return [warning for warning in warnings if isinstance(warning, dict)]


def _theme_preset_payload(name: str) -> dict[str, Any]:
    preset_path = theme_preset_path(name)
    preset = load_theme_preset(name)
    return {
        **preset,
        "path": str(preset_path),
        "sha256": sha256_file(preset_path),
        "resource_uri": f"academic-slides://themes/{preset['name']}",
    }


def _theme_preset_resource_text(name: str) -> str:
    try:
        return json.dumps(_theme_preset_payload(name), indent=2)
    except ThemePresetError as exc:
        return json.dumps(
            {
                "ok": False,
                "error": {"kind": exc.kind, "message": str(exc), "details": exc.details},
            },
            indent=2,
        )
    except OSError as exc:
        return json.dumps(
            {
                "ok": False,
                "error": {"kind": "theme_preset_failed", "message": str(exc), "details": {}},
            },
            indent=2,
        )


def _required_str(
    value: dict[str, Any],
    *,
    field: str,
    kind: str,
    slide_index: int,
    block_index: int | None = None,
) -> str:
    field_value = value.get(field)
    if not isinstance(field_value, str) or not field_value.strip():
        details: dict[str, Any] = {"slide_index": slide_index, "field": field}
        if block_index is not None:
            details["block_index"] = block_index
        raise RichSlideParseError(
            kind=kind,
            message=f"{field} must be a non-empty string.",
            details=details,
        )
    return field_value.strip()


def _png_metadata(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
    metadata = _visual_metadata_from_sidecar(path) or _visual_metadata_from_filename(path)
    result = {
        "path": str(path.resolve()),
        "width": width,
        "height": height,
        "format": "png",
        "sha256": sha256_file(path),
        "dpi": None,
        "scale": None,
        "zoom": None,
        "target": None,
        "page": None,
    }
    result.update(metadata)
    return result


def _slide_bullets(slide: dict[str, Any]) -> list[str] | None:
    if "bullets" in slide:
        bullets = slide["bullets"]
        if not isinstance(bullets, list):
            return None
        if not all(isinstance(item, str) for item in bullets):
            return None
        parsed = [item.strip() for item in bullets if item.strip()]
        return parsed or None
    if "body" not in slide:
        return None
    return _body_to_bullets(str(slide["body"]))


def _body_to_bullets(body: str) -> list[str] | None:
    lines = [
        re.sub(r"^(?:[-*]|\d+[.)])\s*", "", line).strip()
        for line in body.splitlines()
        if line.strip()
    ]
    if len(lines) > 1:
        return lines

    sentence_parts = [
        part.strip() for part in re.split(r"(?<=[.!?])\s+", body.strip()) if part.strip()
    ]
    if len(sentence_parts) > 1:
        return sentence_parts

    words = body.split()
    if not words:
        return None
    chunk_size = 12
    return [
        " ".join(words[index : index + chunk_size]) for index in range(0, len(words), chunk_size)
    ]


def _parse_crop_box(crop: dict) -> CropBox:
    required_fields = {"x", "y", "width", "height"}
    missing_fields = sorted(required_fields.difference(crop))
    if missing_fields:
        raise ValueError(f"Crop is missing required fields: {', '.join(missing_fields)}")
    try:
        crop_box = CropBox(
            x=float(crop["x"]),
            y=float(crop["y"]),
            width=float(crop["width"]),
            height=float(crop["height"]),
            normalized=bool(crop.get("normalized", True)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Crop fields x, y, width, and height must be numeric.") from exc
    if crop_box.width <= 0 or crop_box.height <= 0:
        raise ValueError("Crop width and height must be positive.")
    return crop_box


def _missing_file_result(*, path: str, label: str) -> ToolResult | None:
    resolved = Path(path)
    if resolved.is_file():
        return None
    return ToolResult.error(
        kind="missing_input",
        message=f"{label} not found: {path}",
        details={"path": str(resolved)},
    )


def _parse_render_options(
    *,
    resolution: str,
    dpi: int,
    scale: float,
    zoom: float = 1.0,
) -> RenderOptions:
    options = RenderOptions(
        resolution=resolution,
        dpi=dpi or None,
        scale=scale or None,
        zoom=zoom,
    )
    options.resolved()
    return options


def _validate_manifest_file(*, manifest_path: Path, run_dir: Path) -> dict[str, bool]:
    raw_manifest = manifest_path.read_text(encoding="utf-8")
    try:
        manifest = RunManifest.model_validate_json(raw_manifest)
    except ValidationError:
        return {
            "manifest_parseable": _is_parseable_json(raw_manifest),
            "manifest_schema_valid": False,
            "manifest_run_dir_matches": False,
        }
    return {
        "manifest_parseable": True,
        "manifest_schema_valid": True,
        "manifest_run_dir_matches": manifest.run_dir.resolve() == run_dir,
    }


def _visual_metadata_from_sidecar(path: Path) -> dict[str, Any] | None:
    sidecar_path = path.with_suffix(f"{path.suffix}.json")
    if not sidecar_path.exists():
        return None
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    resolution = payload.get("resolution", {})
    metadata = {
        "dpi": resolution.get("dpi"),
        "scale": resolution.get("scale"),
        "zoom": payload.get("zoom"),
        "target": payload.get("target"),
        "page": payload.get("page"),
    }
    if "quality" in payload:
        metadata["quality"] = payload["quality"]
    return metadata


def _visual_metadata_from_filename(path: Path) -> dict[str, Any]:
    match = re.match(
        r"^(?P<target>source_pdf|deck_pdf)-p(?P<page>\d+)"
        r"(?:-crop)?-(?P<dpi>\d+)dpi(?:-z(?P<zoom>\d+(?:\.\d+)?))?\.png$",
        path.name,
    )
    if match is None:
        return {}
    dpi = int(match.group("dpi"))
    zoom = float(match.group("zoom") or 1.0)
    return {
        "dpi": dpi,
        "scale": dpi / 72,
        "zoom": zoom,
        "target": match.group("target"),
        "page": int(match.group("page")),
    }


def _exception_result(*, kind: str, exc: Exception) -> ToolResult:
    details: dict[str, Any] = {"exception_type": exc.__class__.__name__}
    if isinstance(exc, ValidationError):
        details["validation_errors"] = exc.errors()
    if isinstance(exc, FileNotFoundError):
        details["path"] = exc.filename
    if isinstance(exc, FileExistsError):
        details["path"] = exc.filename
    return ToolResult.error(
        kind=kind,
        message=str(exc),
        details=details,
    )


def _is_parseable_json(raw_json: str) -> bool:
    try:
        json.loads(raw_json)
    except json.JSONDecodeError:
        return False
    return True


_DRAFT_PROMPT = "Draft a Beamer-first academic deck from ingested source artifacts."
_REVIEW_PROMPT = "Review slide validation artifacts and report only evidence-backed issues."
_VISUAL_REVIEW_PROMPT = (
    "Review screenshots, crops, dimensions, and hashes before judging visual quality."
)
_DRAFT_VISUAL_DECK_PROMPT = "\n".join(
    [
        "Draft a visual academic deck using AcademicSlidesHarness MCP tools.",
        "",
        "Hard rules:",
        "- Read `academic-slides://layouts/rich_slide_patterns` before choosing layouts.",
        "- Read `academic-slides://themes/default_visual_academic` before choosing colors.",
        "- If the deck is for Universidade de Brasilia or UnB, read "
        "`academic-slides://themes/unb_visual_academic` and use the UnB colors.",
        "- Call `ListThemePresets` before proposing custom branding.",
        "- Use `RenderLayoutPlaceholders` when you need to see the spatial structure.",
        "- Use `RenderSourcePreview` and `RenderZoomCrop` before selecting visual evidence.",
        "- Prefer `equation_explanation` with `latex_equation` for formulas that can be "
        "transcribed faithfully; do not crop a text-heavy equation screenshot.",
        "- Prefer `table_explanation` with `latex_table` for compact source tables that can be "
        "represented as headers and rows.",
        "- Use crops for irreducible visual evidence: diagrams, plots, handwritten derivations, "
        "source-specific layout evidence, or figures whose geometry matters.",
        "- Call `RenderRichBeamer`; do not fall back to generic bullet-summary decks.",
        "- Every claim must be tied to a source page or visual artifact.",
        "- Keep text inside the layout limits from `academic-slides://schemas/rich_slide_plan`.",
        "- If a source image contains too much embedded PDF text, prefer a tighter crop.",
        "- If the image is too small, low contrast, or illegible, report the risk "
        "instead of using it.",
        "",
        "Required final evidence:",
        "- deck_tex or deck_pdf path",
        "- source previews/crops used, plus any native equations or native tables generated",
        "- slide previews",
        "- layout choices and why each layout was selected",
        "- remaining visual or didactic risks",
    ]
)
_VISUAL_QUALITY_RUBRIC = "\n".join(
    [
        "# Visual Quality Rubric",
        "",
        "Judge rendered PNGs and crops, not TeX alone.",
        "",
        "Checks:",
        "- Visual evidence is relevant to the claim.",
        "- Important details are readable at slide-preview size.",
        "- Crops remove irrelevant PDF text, margins, legends, or neighboring figures "
        "when possible.",
        "- Formula and compact-table slides use native LaTeX when the content can be "
        "reconstructed faithfully.",
        "- A crop is justified only when it preserves visual evidence that native LaTeX cannot.",
        "- The slide has one dominant visual hierarchy: title, evidence, claim, citation.",
        "- Image dimensions, hash, path, DPI, and page metadata are present.",
        "- Low contrast, tiny labels, blur, or clutter are reported as risks.",
    ]
)
_DIDACTIC_QUALITY_RUBRIC = "\n".join(
    [
        "# Didactic Quality Rubric",
        "",
        "A good academic slide teaches one point with visible evidence.",
        "",
        "Checks:",
        "- The title or claim states the point to learn, not just a topic label.",
        "- The learning goal is concrete and short.",
        "- The visual supports the claim instead of decorating the slide.",
        "- Equations are mathematically readable and remain tied to the cited source page.",
        "- Tables are compact enough to be read during a talk.",
        "- Explanatory text is brief enough to be read during a talk.",
        "- Sequential material uses `workflow_steps`, not paragraph bullets.",
        "- Source pages are cited for evidence-bearing slides.",
    ]
)
_TEXT_RESOURCES = (
    (
        "academic-slides://prompts/draft_academic_deck",
        _DRAFT_PROMPT,
        "draft_academic_deck",
        "Prompt for drafting an academic Beamer deck.",
    ),
    (
        "academic-slides://prompts/review_slide_validation",
        _REVIEW_PROMPT,
        "review_slide_validation",
        "Prompt for reviewing deterministic slide validation artifacts.",
    ),
    (
        "academic-slides://prompts/review_visual_artifacts",
        _VISUAL_REVIEW_PROMPT,
        "review_visual_artifacts",
        "Prompt for reviewing screenshot and crop artifacts.",
    ),
    (
        "academic-slides://layouts/rich_slide_patterns",
        layout_catalog_markdown(),
        "rich_slide_patterns",
        "Catalog of supported rich visual slide layout patterns.",
    ),
    (
        "academic-slides://schemas/rich_slide_plan",
        rich_slide_schema_markdown(),
        "rich_slide_plan",
        "Schema and text limits for RenderRichBeamer slide plans.",
    ),
    (
        "academic-slides://prompts/draft_visual_academic_deck",
        _DRAFT_VISUAL_DECK_PROMPT,
        "draft_visual_academic_deck",
        "Prompt for drafting evidence-backed visual academic decks.",
    ),
    (
        "academic-slides://prompts/visual_quality_rubric",
        _VISUAL_QUALITY_RUBRIC,
        "visual_quality_rubric",
        "Rubric for reviewing visual slide artifacts.",
    ),
    (
        "academic-slides://prompts/didactic_quality_rubric",
        _DIDACTIC_QUALITY_RUBRIC,
        "didactic_quality_rubric",
        "Rubric for reviewing slide teaching quality.",
    ),
)


if __name__ == "__main__":
    main()
