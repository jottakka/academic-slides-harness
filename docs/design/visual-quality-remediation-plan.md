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

Status: implemented.

Acceptance:

- full-page source previews cannot be used as `hero_visual` without an override;
- text-heavy crops return a typed error that tells the agent to crop tighter;
- warnings include slide/block indices and artifact path.

Rollback: downgrade hard errors to warnings in the response while preserving the
quality analyzer.

### Chunk 4: Renderer Layout Upgrade

Scope: improve the rich Beamer visual design contract.

Status: implemented for the current rich Beamer templates.

Acceptance:

- title slide is not a blank placeholder;
- citations are small and consistently placed;
- image/text layouts prevent block overlap and preserve visual hierarchy;
- generated slide previews look acceptable at review resolution.

Rollback: keep old layout names and switch rendering internals back per layout.

### Chunk 5: Real MCP Run Acceptance

Scope: rerun the image-processing chapter through stdio MCP and inspect output.

Status: implemented for the chapter fixture real-run acceptance pass.

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

Chunk 3 evidence:

- `RenderRichBeamer` now consumes visual `quality` sidecar metadata before
  copying assets.
- `hero_visual` rejects `page_like_snapshot` with typed
  `visual_quality_failed`.
- Any visual block rejects `text_heavy_crop` with typed
  `visual_quality_failed`.
- `allow_visual_quality_warnings: true` is supported as an explicit exception
  and produces `quality_override: true` in asset metadata.
- Targeted failing-first test was:
  `uv run pytest tests/test_mcp_contracts.py -q -k "quality or snapshot or text_heavy"`.

Chunk 4 evidence:

- `render_rich_beamer_tex` now emits an academic opening frame with deck focus,
  structure summary, and cited source pages.
- Rich frames disable the default Beamer footline to avoid date/counter chrome.
- Source citations render through a small `\ashsourcecitation` command instead
  of full-size block content.
- `figure_explanation` uses a larger visual column, a compact right rail, and a
  capped image height.
- Non-visual claim/explanation slides use custom clean surfaces instead of
  default Beamer block title bars.
- Real stdio MCP render/compile/preview smoke:
  `runs/layout-upgrade-stdio-20260511002448/layout-upgrade-stdio-report.json`.
- Preview artifacts inspected manually:
  - `runs/layout-upgrade-stdio-20260511002448/previews/deck_pdf-p1-144dpi.png`
  - `runs/layout-upgrade-stdio-20260511002448/previews/deck_pdf-p2-144dpi.png`
  - `runs/layout-upgrade-stdio-20260511002448/previews/deck_pdf-p3-144dpi.png`

## Chunk 5 Evidence

Chunk 5 evidence:

- Source fixture:
  `tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf`.
- Real stdio MCP run report:
  `runs/chunk5-real-chapter-20260511003209/chunk5-final-deck-refined-report.json`.
- Compiled PDF:
  `runs/chunk5-real-chapter-20260511003209/compiled-refined/deck.pdf`.
- Source crop contact sheet:
  `runs/chunk5-real-chapter-20260511003209/crop-contact-sheet-refined.jpg`.
- Deck previews inspected manually:
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p1-144dpi.png`
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p2-144dpi.png`
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p3-144dpi.png`
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p4-144dpi.png`
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p5-144dpi.png`
  - `runs/chunk5-real-chapter-20260511003209/deck-previews-refined/deck_pdf-p6-144dpi.png`
- All six deck previews reported no deterministic quality warnings.
- First deck iteration was rejected because the hero slide hid the citation and
  some crops still carried caption/text residue; the refined pass corrected both.

## Next Work

Implement a deterministic rich-deck quality validator instead of relying on
manual inspection notes. It should score/return typed failures for missing
citations, insufficient visual evidence, hard visual warnings, too many text-only
slides, and rendered-preview quality warnings.

## 2026-05-11 ESN Run Findings

The ESN Aula 11 deck run exposed a different failure mode from the earlier
image-processing fixture: source crops were used for equations and dense tables
because the rich schema only offered visual crops, claims, explanations, steps,
and citations.

Root causes:

- `RenderRichBeamer` had no native equation or table block, so agents treated
  formulas as visual evidence.
- `allow_visual_quality_warnings: true` could bypass the `text_heavy_crop` gate
  even when the better fix was native LaTeX transcription.
- Prompt resources over-emphasized `RenderZoomCrop` and did not tell agents to
  use native LaTeX for reconstructable math.
- The ESN generation path used `pdfplumber` excerpts plus PyMuPDF previews and
  crops; it did not use MarkItDown Markdown extraction.
- PT-BR decks with accents are a QA risk whenever text is generated through a
  non-UTF-8 shell path. Rich Beamer output should keep UTF-8 explicit in the
  generated preamble.

Implemented mitigation:

- Added `equation_explanation` with a `latex_equation` block.
- Added `table_explanation` with a structured `latex_table` block rendered as
  Beamer `tabular`.
- Added prompt/schema guidance: use crops for diagrams, plots, handwritten
  derivations, source-specific layout evidence, or figures whose geometry
  matters; use native LaTeX for equations and compact tables that can be
  reconstructed faithfully.
- Added the `unb_visual_academic` theme preset so agents do not invent UnB
  branding on each run.

Remaining improvements:

- Implement deterministic deck-level quality validation that flags overuse of
  `allow_visual_quality_warnings`.
- Add `ExtractSourceMarkdown` so MarkItDown can provide cleaner whole-document
  planning text alongside page-cited `ExtractSourcePages`.
- Add a source-to-native-math helper that proposes candidate LaTeX equations and
  tables from extracted Markdown/text, but still requires deterministic schema
  validation and source-page citation.
- Add a final rendered-preview checker for PT-BR accent corruption before a deck
  is copied to `Downloads`.
