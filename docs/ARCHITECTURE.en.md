# Architecture And MCP Tools

Academic Slides Harness is a deterministic, LaTeX-first system for producing
academic slide decks from source PDFs. It is designed so an agent can plan and
render a deck while every important intermediate artifact remains inspectable.

## System Boundaries

- `src/academic_slides_harness/core`: Pydantic models, hashes, run manifests,
  state-machine definitions, and shared result contracts.
- `src/academic_slides_harness/ingest`: PDF inspection and page text extraction.
- `src/academic_slides_harness/render`: Beamer rendering, rich visual layouts,
  theme presets, and Tectonic compilation.
- `src/academic_slides_harness/visualize`: PDF-to-PNG previews, zoom crops,
  render options, image sanitization, and deterministic visual quality metrics.
- `src/academic_slides_harness/llm`: optional provider adapters and deterministic
  fallback behavior, plus redacted provider discovery.
- `src/academic_slides_harness/mcp`: Arcade MCP app construction, tool
  registration, resources, structured outputs, and typed errors.

Production code lives under `src/academic_slides_harness`. Tests live under
`tests`. Generated runs should stay under `runs/` or another caller-provided
output directory.

## Pipeline

The intended pipeline is:

```text
create run
  -> ingest source PDF
  -> extract selected page text
  -> render source previews and crops
  -> plan slide content
  -> render Beamer or rich Beamer source
  -> compile PDF with Tectonic
  -> render slide previews and crops
  -> validate rendered layout overflow
  -> list visual artifacts
  -> validate run
```

The pipeline state model is:

```text
created -> ingesting -> ingested -> planning -> planned -> rendering -> rendered
-> visualizing -> visualized -> validating -> validated|failed
```

Tool execution state is:

```text
idle -> received -> eliciting|running -> progress -> completed|tool_error|fatal_error
```

The current implementation exposes tools, resources, prompts, structured
outputs, and typed errors. Full task/progress/elicitation behavior is design
direction, not a public-ready feature claim yet.

## MCP Transport

The stable local entrypoint is stdio:

```powershell
uv run python server.py stdio
```

`server.py` starts `academic_slides_harness.mcp.server:main`. The server accepts
`stdio` by default and also accepts `http`, but stdio is the validated default.

Arcade can run the stdio server from the repository root:

```powershell
arcade mcp stdio --cwd .
```

HTTP endpoint checks are opt-in diagnostics:

```powershell
uv run academic-slides-harness doctor arcade --check-http-endpoints --json
```

## MCP Tool Catalog

Generation and run management:

- `AcademicSlidesHarness_CreateRun`: create a run directory, screenshots folder,
  and `manifest.json`.
- `AcademicSlidesHarness_ValidateRun`: validate the run directory, screenshots
  folder, and manifest schema.

Source ingestion and planning:

- `AcademicSlidesHarness_IngestSource`: inspect a PDF and return metadata.
- `AcademicSlidesHarness_ExtractSourcePages`: return selected page text excerpts.
- `AcademicSlidesHarness_ListModelProviders`: report redacted local/configured
  model-provider availability for deterministic versus optional model-assisted
  routing.
- `AcademicSlidesHarness_PlanDeck`: create a deterministic draft plan from text
  excerpts using the fallback provider.

Rendering and compilation:

- `AcademicSlidesHarness_RenderBeamer`: render v0 compatibility Beamer from
  simple slide objects.
- `AcademicSlidesHarness_RenderRichBeamer`: render typed rich slides with visual
  blocks, citations, text limits, sanitized image assets, and rich layouts.
- `AcademicSlidesHarness_CompileRenderedBeamer`: compile generated `.tex` with
  Tectonic.

Visual artifacts:

- `AcademicSlidesHarness_RenderSourcePreview`: render PDF source pages to PNG.
- `AcademicSlidesHarness_RenderSlidePreview`: render compiled deck pages to PNG.
- `AcademicSlidesHarness_RenderZoomCrop`: render a focused crop from a source or
  deck PDF.
- `AcademicSlidesHarness_ValidateLayoutOverflow`: inspect deck preview PNGs for
  ink inside protected layout regions and optional Tectonic overfull boxes,
  returning evidence crops for failures.
- `AcademicSlidesHarness_ListVisualArtifacts`: list PNG artifacts and metadata.

Rich deck helpers:

- `AcademicSlidesHarness_RenderLayoutPlaceholders`: generate PNG placeholder
  previews for rich layouts.
- `AcademicSlidesHarness_ListThemePresets`: list deterministic visual theme
  presets.

## MCP Resource Catalog

Current public resources include:

- `academic-slides://layouts/rich_slide_patterns`
- `academic-slides://schemas/rich_slide_plan`
- `academic-slides://prompts/draft_visual_academic_deck`
- `academic-slides://prompts/review_slide_validation`
- `academic-slides://prompts/review_visual_artifacts`
- `academic-slides://prompts/visual_quality_rubric`
- `academic-slides://prompts/didactic_quality_rubric`
- `academic-slides://themes/default_visual_academic`
- `academic-slides://themes/unb_visual_academic`

These resources guide agents toward evidence-backed visual decks instead of
generic bullet-summary decks.

## Artifact Contract

MCP-facing visual tools should return structured data that includes:

- absolute artifact path;
- width and height;
- target (`source_pdf` or `deck_pdf`);
- page or slide number;
- resolution preset;
- DPI, scale, and zoom;
- SHA-256 hash;
- quality metadata and warnings when available.

Sidecars use `.png.json` next to generated PNGs. Callers should use the sidecar
metadata before falling back to filename parsing.

## Error Contract

Tools return typed errors instead of leaking low-level exceptions when practical.
Examples include:

- `missing_input`
- `invalid_page_selection`
- `invalid_crop`
- `invalid_render_options`
- `artifact_exists`
- `validation_failed`
- `compile_failed`
- `compile_timeout`
- `invalid_visual_artifact`
- `image_too_small`
- `visual_quality_failed`
- `text_overflow_risk`
- `layout_overflow_detected`

This makes the tools usable by agents that need to recover or choose a narrower
next step.

## Implemented, Experimental, Planned

Implemented:

- PDF ingestion and page text extraction.
- Simple and rich Beamer rendering.
- Tectonic compilation when the executable is available.
- Source/deck previews, zoom crops, artifact listing, hashes, sidecars, and
  visual quality warnings.
- MCP stdio tools/resources with typed errors.
- Local Arcade, model-provider, and secret diagnostics.

Experimental:

- Rich visual deck quality gates. Several visual warning checks are implemented,
  but a full deterministic deck-level validator is still planned.
- HTTP transport and HTTP endpoint checks.

Planned:

- Video ingestion.
- Public contribution/security governance files.

## Validation Matrix

Normal local gate:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

MCP/Arcade gate:

```powershell
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Optional gates:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run pytest -m ollama -q
uv run academic-slides-harness doctor models --json
uv run academic-slides-harness doctor secrets --json
```

`arcade_live` means local stdio MCP runtime smoke. It is not an HTTP worker or
engine check.
