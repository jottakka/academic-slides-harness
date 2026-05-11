# Ticket 5 Image Sanitization Handoff

## Objective

Implement Ticket 5 from `docs/design/visual-rich-deck-roadmap.md`: make visual
assets safe and predictable before `RenderRichBeamer` copies them into Beamer
output.

## Local Findings

- Repo rules require `uv`, TDD, structured MCP errors, and `arcade_live` for
  MCP-facing changes.
- Existing rich rendering copies visual assets in
  `src/academic_slides_harness/mcp/server.py` through `_copy_visual_asset`.
- Current behavior checks `is_file()` and extension only, then copies the file.
- Existing tests cover rich Beamer asset copying and missing visual artifacts in
  `tests/test_mcp_contracts.py`.
- Existing visual utility tests live in `tests/test_visualize.py`; initial
  exploration found no image sanitizer module yet.
- MCP public signatures must stay JSON-friendly and must not expose `Path`.

## Execution Plan

1. Scope: add focused failing tests for image sanitization.
   Acceptance: tests cover valid PNG/JPEG metadata, corrupt image rejection,
   tiny image rejection, and rich renderer typed errors.
   Risk: tests may overfit implementation names.
   Rollback: remove only the new test cases.

2. Scope: add deterministic sanitizer module under `visualize`.
   Acceptance: validates readable images, supported formats, minimum
   dimensions, mode normalization, and returns structured metadata.
   Risk: Pillow behavior differs by image mode or format.
   Rollback: delete the new module and restore direct copy path.

3. Scope: integrate sanitizer into `RenderRichBeamer` asset copying.
   Acceptance: `assets` response includes sanitized metadata, deck path, source
   path, hash, dimensions, format, mode, and conversion flag.
   Risk: existing consumers expect only source/deck/hash fields.
   Rollback: keep old fields stable and remove only additive sanitizer fields.

4. Scope: update local handoff and roadmap status.
   Acceptance: docs state what was implemented and how it was validated.
   Risk: docs overclaim if QA fails.
   Rollback: mark partial status and list residual risk.

5. Scope: run QA and code review.
   Acceptance: targeted tests, non-live suite, lint/format, doctor arcade, and
   `arcade_live` are run or explicitly documented as blocked.
   Risk: live stdio dependencies can fail independently of code changes.
   Rollback: document blocker without weakening production tests.

6. Scope: commit and push a scoped branch.
   Acceptance: only intended files are staged, commit exists locally, and branch
   is pushed to `origin`.
   Risk: remote auth/network failure.
   Rollback: keep local commit and report push blocker.

## Out Of Scope

- Image legibility scoring, contrast metrics, and crop-quality warnings.
- New MCP tools for standalone sanitization.
- Theme preset application in `RenderRichBeamer`.
- End-to-end agent deck generation.
- HTTP transport validation.

## Success Criteria

- Corrupt images fail before being copied into deck output.
- Tiny images fail before being copied into deck output.
- Valid PNG/JPEG assets are accepted and reported with stable metadata.
- Visual asset handling remains deterministic and backward-compatible for
  existing `assets` fields.
- MCP-facing rich render errors are typed and machine-readable.

## QA Plan

```powershell
uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
git diff --check
```

## Completion Notes

Implemented.

## Completed Scope

- Added `src/academic_slides_harness/visualize/sanitize.py`.
- Added focused sanitizer tests for valid PNG metadata, readable non-PNG/JPEG
  conversion, corrupt image rejection, and tiny image rejection.
- Integrated sanitization into `RenderRichBeamer` visual asset copying.
- Preserved existing `assets` fields: `source_path`, `deck_path`, and `sha256`.
- Added asset metadata: `path`, `width`, `height`, `format`, `mode`,
  `source_sha256`, and `converted`.
- Updated rich slide schema guidance and roadmap status.
- Added Pillow as a direct runtime dependency because production code imports
  `PIL`.

## QA Evidence

- Initial failing test observed:
  `uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q`
  failed with `ModuleNotFoundError: No module named
  'academic_slides_harness.visualize.sanitize'`.
- `uv run ruff format --check .` -> passed, 35 files already formatted.
- `uv run ruff check .` -> passed.
- `uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q` ->
  passed, 75 tests.
- `uv run pytest tests/test_render.py tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
  -> passed, 61 tests.
- `uv run pytest -m "not ollama and not arcade_live" -q` -> passed, 111 tests
  and 2 deselected.
- `uv run academic-slides-harness doctor arcade --json` -> passed; Arcade CLI
  and local stdio entrypoint were available.
- `uv run pytest -m arcade_live -q` -> passed, 1 test and 112 deselected.
- `git diff --check` -> passed with CRLF conversion warnings only.

## Decisions

- Kept sanitization internal instead of adding a new MCP tool; this matches the
  Ticket 5 scope.
- Used 16x16 as the minimum visual dimension so existing rich-render fixtures
  remain valid while clearly rejecting tiny placeholder images.
- Treated `sha256` as the sanitized deck asset hash and added `source_sha256`
  for the original input. For unchanged PNG/JPEG pass-through files, both hashes
  are identical.
- Allowed readable non-PNG/JPEG formats to normalize to PNG, matching the
  roadmap wording that images may be convertible to PNG.

## Pending

- Ticket 6 should add image legibility and crop-quality scoring.
- Ticket 7 should add deterministic visual/didactic deck validation.
