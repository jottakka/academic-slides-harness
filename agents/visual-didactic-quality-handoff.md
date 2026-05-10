# Visual Didactic Quality Handoff

## Objective

Improve Academic Slides Harness so agents can produce visually and didactically
useful decks, not generic bullet-summary Beamer files.

## Non-Negotiable Rules

- Read `AGENTS.md` before edits.
- Use `uv`.
- Start behavior changes with a failing test.
- Keep MCP parameters JSON-friendly.
- Do not expose raw `Path` parameters in MCP tools.
- Do not use raw LaTeX as the primary agent contract.
- Generated runs and screenshots stay outside tracked paths.
- For MCP-facing changes, run `doctor arcade` and `arcade_live`.

## Do Not Fake MCP

When validating MCP behavior, call the MCP tool through stdio MCP. Do not create
scripts or direct Python wrappers as a substitute. If tools are not available or
the call is cancelled, stop and report that blocker.

## Ticket Order

1. Rich slide schema and `RenderRichBeamer`.
2. MCP prompt/resources for visual academic decks and quality rubrics.
3. Deterministic visual/didactic quality validator.
4. MCP-only agent E2E deck run with real source visuals.

## Owned Files By Ticket

Ticket 1:

- `src/academic_slides_harness/render/beamer.py`
- `src/academic_slides_harness/mcp/server.py`
- `tests/test_render.py`
- `tests/test_mcp_contracts.py`
- `tests/test_mcp_stdio.py`
- `tests/test_arcade_live.py`

Ticket 2:

- `src/academic_slides_harness/mcp/server.py`
- `tests/test_mcp_contracts.py`
- `tests/test_mcp_stdio.py`
- `docs/design/visual-rich-deck-roadmap.md`

Ticket 3:

- `src/academic_slides_harness/validate/` or equivalent validator module
- `tests/test_*quality*.py`
- E2E fixture tests that render previews/crops

Ticket 4:

- No production code unless a validated blocker appears.
- Generated artifacts under `runs/`.
- Final report with paths, screenshots, crops, and quality assessment.

## Validation Commands

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

For rich render changes also run:

```powershell
uv run pytest tests/test_render.py tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q
```

## Final Checklist

- Failing test was observed before implementation.
- Rich layouts do not collapse into `itemize`.
- Real visual assets are copied into the deck output.
- TeX compiles when Tectonic is available.
- PNG previews or crops exist for visual claims.
- MCP stdio discovers and calls the changed tool.
- `git diff --check` passes.
- Commit stages only scoped files.

## MCP-Only Agent Prompt

```text
You are generating or validating an Academic Slides Harness deck.

Hard rules:
- Use only AcademicSlidesHarness MCP tools.
- Do not use shell, scripts, wrappers, or direct Python calls as fallback.
- If an MCP tool is unavailable, cancelled, or fails, stop and report the exact tool and error.
- Use rich visual layouts when source previews or crops are available.
- Each claim must cite a source page or visual artifact.
- A compiled deck that is only generic bullet slides is not acceptable.

Required flow:
1. CreateRun.
2. IngestSource.
3. RenderSourcePreview for visual pages.
4. RenderZoomCrop for at least one visual detail.
5. ExtractSourcePages for the selected pages.
6. RenderRichBeamer using source visuals and evidence-backed blocks.
7. CompileRenderedBeamer.
8. RenderSlidePreview for all slides.
9. RenderZoomCrop for at least one deck slide.
10. ListVisualArtifacts.
11. ValidateRun.

Final report:
- run_dir
- deck_pdf
- source previews
- slide previews
- zoom crops
- validation status
- quality assessment: visual quality, didactic quality, consistency, and evidence use
```
