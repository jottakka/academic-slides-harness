# Visual Quality Remediation Plan

## Problem From Real Run

The Ticket 5 real run proved the pipeline can create a rich Beamer PDF through
stdio MCP, but the visual and academic output was poor:

- the title slide was a blank centered title with no academic framing;
- one hero slide embedded a full source PDF page instead of a focused visual;
- one figure slide used a crop dominated by paragraph text;
- the final slide described harness artifacts instead of teaching image
  processing;
- the renderer accepted all of this because current validation checks file
  existence, dimensions, hashes, and compilation, not visual teaching quality.

## Root Causes

- `RenderSourcePreview` and `RenderZoomCrop` do not report whether an artifact is
  page-like, mostly blank, low-contrast, or text-heavy.
- `RenderRichBeamer` trusts every sanitized image that is technically readable.
- Rich layouts use fixed Beamer blocks and do not reserve a small, consistent
  citation/reference position.
- There is no deterministic deck-quality validator that rejects visually weak
  decks before final acceptance.
- Agent-facing prompts ask for better choices, but no tool gives machine-readable
  quality warnings that an agent must obey.

## Chunk Plan

### Chunk 1: Visual Artifact Quality Metrics

Scope: add deterministic image metrics for PNG artifacts.

Status: implemented.

Acceptance:

- blank/near-blank images get a `low_visual_density` warning;
- low-contrast images get a `low_contrast` warning;
- portrait full-page screenshots get a `page_like_snapshot` warning;
- crops dominated by small text components get a `text_heavy_crop` warning;
- normal figure-like images return no blocking warning.

Rollback: remove the new quality module and tests.

### Chunk 2: Preview/Crop Metadata Integration

Scope: include quality metrics and warnings in source preview, slide preview, and
zoom crop artifact structured content and sidecars.

Status: implemented for artifact metadata and `ListVisualArtifacts` propagation.

Acceptance:

- `RenderSourcePreview` returns `quality` metadata per artifact;
- `RenderZoomCrop` returns `quality` metadata per artifact;
- existing path/dimension/hash fields remain unchanged;
- tests cover both direct helper calls and MCP-facing structured output.

Rollback: keep the quality module but stop attaching quality to
`ScreenshotArtifact`.

### Chunk 3: Rich Deck Quality Gate

Scope: reject or warn when `RenderRichBeamer` uses a visual artifact with hard
quality warnings.

Acceptance:

- full-page source previews cannot be used as `hero_visual` without an override;
- text-heavy crops return a typed error that tells the agent to crop tighter;
- warnings include slide/block indices and artifact path.

Rollback: downgrade hard errors to warnings in the response while preserving the
quality analyzer.

### Chunk 4: Renderer Layout Upgrade

Scope: improve the rich Beamer visual design contract.

Acceptance:

- title slide is not a blank placeholder;
- citations are small and consistently placed;
- image/text layouts prevent block overlap and preserve visual hierarchy;
- generated slide previews look acceptable at review resolution.

Rollback: keep old layout names and switch rendering internals back per layout.

### Chunk 5: Real MCP Run Acceptance

Scope: rerun the image-processing chapter through stdio MCP and inspect output.

Acceptance:

- deck compiles;
- preview artifacts exist;
- validator reports no hard visual warnings;
- manual screenshot review confirms it is not a bland placeholder deck.

## Immediate Out Of Scope

- LLM-based visual judgment.
- OCR dependencies.
- Full automatic figure extraction from PDFs.
- Theme preset application beyond the current renderer.

## Checkpoint Evidence

Commands passed:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest tests/test_visual_quality.py tests/test_visualize.py tests/test_mcp_contracts.py -q`
- `uv run pytest tests/test_render.py tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`

Real MCP stdio warning smoke:

- Run report:
  `runs/visual-quality-warning-smoke-20260511000630/visual-quality-warning-report.json`.
- `source_pdf-p1-144dpi.png` now reports `page_like_snapshot` and
  `text_heavy_crop`.
- `source_pdf-p4-144dpi.png` now reports `page_like_snapshot` and
  `text_heavy_crop`.
- `source_pdf-p4-crop-144dpi-z2.5.png` now reports `text_heavy_crop`.

## Next Chunk

Implement Chunk 3: make `RenderRichBeamer` consume quality metadata and reject
hard visual misuse before rendering, especially:

- `hero_visual` using a `page_like_snapshot`;
- visual blocks using `text_heavy_crop` without an explicit override;
- source/crop warnings without slide/block-indexed typed feedback.
