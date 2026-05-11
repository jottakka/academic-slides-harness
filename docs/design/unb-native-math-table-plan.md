# UnB Theme And Native Math/Table Slide Contract

Date: 2026-05-11

## Goal

Add a portable UnB visual academic theme preset and improve the MCP rich-deck
contract so equations and tables are preferably rendered as native LaTeX blocks,
not as large source-PDF crops.

## Execution Plan

1. Add tests for UnB theme discovery.
   - Scope: theme loader, MCP preset list, and resource registry.
   - Acceptance: tests expect `unb_visual_academic` with UnB blue/green and a
     theme resource URI.
   - Risk: resource list becomes stale when more presets are added.
   - Rollback: remove the new preset JSON and registry/listing changes.

2. Add tests for native equation and table blocks.
   - Scope: `RenderRichBeamer` parsing plus Beamer TeX generation.
   - Acceptance: valid `latex_equation` and `latex_table` blocks render without
     visual assets; unsafe equation commands return typed errors.
   - Risk: raw LaTeX can become an injection surface.
   - Rollback: remove new block types and keep crop-only visual flow.

3. Implement the UnB preset first.
   - Scope: `templates/themes`, theme listing helper, MCP resources.
   - Acceptance: `ListThemePresets` returns default and UnB presets; both
     resources are registered.
   - Risk: logo file is not portable.
   - Rollback: keep `logo.path` null and document how callers may provide a run
     artifact logo separately.

4. Implement native equation/table layouts.
   - Scope: render dataclasses, schema/prompt resources, MCP parser and typed
     errors.
   - Acceptance: equations/tables compile as LaTeX, cite source pages, and do
     not require screenshot crops.
   - Risk: generated formulas may exceed slide width.
   - Rollback: keep layouts but reject overly long LaTeX until a fitter is added.

5. Document the ESN run findings and MarkItDown status.
   - Scope: visual remediation and MarkItDown plan docs.
   - Acceptance: docs explain why large crops happened, when crops are still
     valid, and that MarkItDown is not yet used by the current deck path.
   - Risk: docs overpromise MarkItDown equation fidelity.
   - Rollback: mark MarkItDown as planned extraction only.

6. Run QA and publish a scoped checkpoint.
   - Scope: targeted tests, formatting/lint, full non-live suite, arcade doctor,
     and `arcade_live` because MCP resources/contracts changed.
   - Acceptance: commands pass or residual risk is documented with exact failure.
   - Risk: live Arcade setup may be unavailable locally.
   - Rollback: no production rollback needed if tests fail before commit.

## Out Of Scope

- Automatic source-PDF formula recognition.
- Full MarkItDown `ExtractSourceMarkdown` implementation.
- OCR or cloud model extraction.
- Bundling official UnB logo assets into tracked source paths.
- Regenerating the ESN deck in this chunk.

## Technical Success Criteria

- `unb_visual_academic` is loadable and visible through MCP.
- `equation_explanation` and `table_explanation` are supported rich layouts.
- Prompt/schema resources instruct agents to prefer native LaTeX for
  reconstructable formulas and tables.
- Unsafe LaTeX commands fail with typed MCP errors.

## QA Criteria

- Targeted tests fail before implementation and pass after.
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`
