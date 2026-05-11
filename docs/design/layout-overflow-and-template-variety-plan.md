# Layout Overflow And Template Variety Plan

Date: 2026-05-11

Status: implemented in this chunk.

## Goal

Reduce repeated left-content/right-rail decks and catch rendered overflow before
a deck is handed to a user. The ESN deck showed that a Beamer PDF can compile
successfully while a long formula visually crosses into the neighboring column.

## Chunk Plan

1. Add deterministic rendered-layout overflow analysis.
   - Scope: inspect PNG previews and optional Tectonic logs.
   - Acceptance: synthetic tests detect ink inside a protected gutter/region and
     parse `Overfull \hbox` warnings.
   - Risk: image regions are template-specific.
   - Rollback: remove the new module and MCP tool; existing visual-quality
     checks stay unchanged.

2. Expose an MCP `ValidateLayoutOverflow` tool.
   - Scope: JSON-friendly screenshot directory, output directory, optional
     normalized protected regions, optional Tectonic log.
   - Acceptance: returns structured results with paths, dimensions, hashes,
     region metrics, warning kind, and typed errors.
   - Risk: default regions may not match every slide design.
   - Rollback: keep the lower-level module and remove the MCP registration.

3. Add template variety guidance to the layout catalog.
   - Scope: new patterns for correction pipelines, derivations, concept
     matrices, two-equation comparisons, mode plots, and checklist summaries.
   - Acceptance: `RenderLayoutPlaceholders` can render these names and the MCP
     resource documents when to use each one.
   - Risk: initial render internals may still use generic fallback for new
     layouts until richer renderers are added.
   - Rollback: remove the new catalog entries and docs.

## Out Of Scope For This Chunk

- Full semantic overlap detection without template regions.
- Automatic PowerPoint-like layout solving.
- Rewriting the ESN deck generation script into a reusable deck planner.
- OCR or LLM-based visual judgement.

## QA

- Targeted failing-first tests for overflow module, MCP contract, and template
  placeholders.
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`

## Implementation Handoff

Implemented:

- Added `academic_slides_harness.visualize.overflow` with deterministic
  protected-region ink analysis and TeX `Overfull`/`Underfull` box parsing.
- Added MCP tool `AcademicSlidesHarness_ValidateLayoutOverflow`.
- Added overflow evidence crops for failing protected regions, including path,
  dimensions, and SHA-256.
- Expanded rich layout catalog with:
  `correction_pipeline`, `derivation_steps`, `concept_matrix`,
  `two_equation_comparison`, `mode_plot`, and `checklist_summary`.
- Added placeholder drawings and schema guidance for the new academic layouts.
- Updated architecture docs and visual-deck prompt guidance so future agents
  call layout overflow validation after slide previews.

QA evidence:

- `uv run pytest tests/test_layout_overflow.py tests/test_mcp_contracts.py -q -k "overflow or varied_academic_templates or tool_registry or stdio_contract"`
  passed with 11 tests.
- `uv run ruff format --check .` passed.
- `uv run ruff check .` passed.
- `uv run pytest -m "not ollama and not arcade_live" -q` passed with
  144 tests.
- `uv run academic-slides-harness doctor arcade --json` passed.
- `uv run pytest -m arcade_live -q` passed and now calls
  `AcademicSlidesHarness_ValidateLayoutOverflow` over real stdio MCP.

Residual risks:

- Default protected regions are intentionally conservative; high-quality decks
  should pass template-specific regions when the slide has custom columns,
  equation bands, or rails.
- The detector is deterministic image analysis, not semantic layout solving.
  It catches ink in guarded areas and TeX box warnings, but it does not prove
  that every text hierarchy is aesthetically balanced.
