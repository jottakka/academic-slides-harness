import json
import re
import sys
from pathlib import Path
from typing import Annotated, Any

from arcade_mcp_server import MCPApp
from PIL import Image

from academic_slides_harness.core.models import RunManifest, ToolResult, sha256_bytes
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
        "compile_rendered_beamer",
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
    slug = _slug(title)
    if not slug:
        return ToolResult.error(
            kind="invalid_title",
            message="Run title must include at least one alphanumeric character.",
        )
    run_dir = Path(base_dir).resolve() / slug
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
    slides: Annotated[
        list[dict[str, Any]], "Slide objects with title and bullets fields, or body fields."
    ],
) -> ToolResult:
    """Render a Beamer deck.tex file from structured slide data."""
    parsed_slides: list[BeamerSlide] = []
    for index, slide in enumerate(slides, start=1):
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
            "sha256": sha256_bytes(tex_path.read_bytes()),
        },
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
        "manifest_exists": (path / "manifest.json").exists(),
    }
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
    try:
        artifacts = render_pdf_pages(
            pdf_path=Path(source_pdf),
            output_dir=Path(output_dir),
            target="source_pdf",
            pages=selected_pages,
            options=render_options,
        )
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
    try:
        artifacts = render_pdf_pages(
            pdf_path=Path(deck_pdf),
            output_dir=Path(output_dir),
            target="deck_pdf",
            pages=selected_slides,
            options=render_options,
        )
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
    try:
        artifact = render_crop(
            pdf_path=Path(pdf_path),
            output_dir=Path(output_dir),
            target=target,
            page=page,
            crop=crop_box,
            options=render_options,
        )
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
    png_paths = sorted(directory.rglob("*.png")) if directory.exists() else []
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
    try:
        pdf_path = compile_tex_with_tectonic(tex_path=Path(tex_path), output_dir=Path(output_dir))
    except Exception as exc:
        return _exception_result(kind="compile_failed", exc=exc)
    return ToolResult.success(
        message="Compiled Beamer PDF",
        structured_content={
            "pdf_path": str(pdf_path.resolve()),
            "sha256": sha256_bytes(pdf_path.read_bytes()),
        },
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
        compile_rendered_beamer,
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


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    transport = args[0] if args else "stdio"
    if transport not in {"stdio", "http"}:
        raise SystemExit(f"Unsupported transport '{transport}'. Use 'stdio' or 'http'.")
    build_app().run(transport=transport)


def _slug(title: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in title).strip("-")


def _png_metadata(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
    metadata = _visual_metadata_from_sidecar(path) or _visual_metadata_from_filename(path)
    result = {
        "path": str(path.resolve()),
        "width": width,
        "height": height,
        "format": "png",
        "sha256": sha256_bytes(path.read_bytes()),
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
        parsed = [str(item).strip() for item in bullets if str(item).strip()]
        return parsed or None
    if "body" not in slide:
        return None
    return _body_to_bullets(str(slide["body"]))


def _body_to_bullets(body: str) -> list[str] | None:
    lines = [re.sub(r"^[-*]\s*", "", line).strip() for line in body.splitlines() if line.strip()]
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


def _visual_metadata_from_sidecar(path: Path) -> dict[str, Any] | None:
    sidecar_path = path.with_suffix(f"{path.suffix}.json")
    if not sidecar_path.exists():
        return None
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    resolution = payload.get("resolution", {})
    return {
        "dpi": resolution.get("dpi"),
        "scale": resolution.get("scale"),
        "zoom": payload.get("zoom"),
        "target": payload.get("target"),
        "page": payload.get("page"),
    }


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
    return ToolResult.error(
        kind=kind,
        message=str(exc),
        details={"exception_type": exc.__class__.__name__},
    )


_DRAFT_PROMPT = "Draft a Beamer-first academic deck from ingested source artifacts."
_REVIEW_PROMPT = "Review slide validation artifacts and report only evidence-backed issues."
_VISUAL_REVIEW_PROMPT = (
    "Review screenshots, crops, dimensions, and hashes before judging visual quality."
)


if __name__ == "__main__":
    main()
