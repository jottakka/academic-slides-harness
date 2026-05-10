# Visual Rich Deck Roadmap

## Problem

The current deck path can ingest PDFs, render source previews, compile Beamer, and
validate visual artifacts, but the produced deck is visually and didactically weak.
The root cause is the contract: `render_beamer` accepts only `title` plus bullets
and always emits a Madrid `itemize` frame. Agents can select evidence, but they
cannot express layout, source-image placement, explanation structure, or visual
hierarchy.

## Target Outcome

Agents should generate evidence-backed academic decks that are deterministic to
render and easy to validate:

- Slides use source images or crops when the source is visual.
- Claims cite source pages or artifacts.
- Layouts vary by teaching purpose instead of defaulting to bullet lists.
- Text is short, structured, and tied to a learning goal.
- Visual quality is checked from rendered PNGs and zoom crops, not from TeX alone.

## Non-Negotiable Limits

- Do not make raw LaTeX the primary agent contract.
- Keep MCP parameters JSON-friendly; accept strings and dictionaries, not `Path`.
- Preserve the old `render_beamer` tool for backward compatibility.
- Every new MCP-facing tool needs typed errors and stdio MCP coverage.
- Generated run artifacts stay under `runs/` or temp directories, not tracked paths.

## Ticket 1: Rich Beamer Rendering

Goal: add a deterministic rich-slide renderer and MCP tool that can place real
visual artifacts into slides.

Status: implemented as the first vertical slice. Continue to refine layout
quality in later tickets instead of overloading this initial renderer.

Files likely touched:

- `src/academic_slides_harness/render/beamer.py`
- `src/academic_slides_harness/mcp/server.py`
- `tests/test_render.py`
- `tests/test_mcp_contracts.py`
- `tests/test_mcp_stdio.py`

Minimum schema:

```json
{
  "title": "Segmenting the nuclear rim",
  "layout": "figure_explanation",
  "learning_goal": "Explain why rim segmentation is the measurement anchor.",
  "blocks": [
    {"type": "visual", "artifact_path": "C:/abs/path/source_pdf-p21-144dpi.png"},
    {"type": "claim", "text": "Intensity dynamics are measured at compartment boundaries."},
    {"type": "explanation", "text": "The highlighted rim converts a cell image into a reproducible measurement region."},
    {"type": "source_citation", "source_page": 21}
  ]
}
```

Acceptance criteria:

- A rich slide can render a PNG with `\includegraphics`.
- At least one rich layout avoids `itemize`.
- Invalid visual paths return typed MCP errors.
- The compiled PDF renders to a PNG preview.
- `arcade_live` passes after the MCP tool is added.

Implemented contract:

- MCP tool: `RenderRichBeamer`.
- Rich layouts: `hero_visual`, `figure_explanation`, `workflow_steps`, `takeaway`.
- Rich blocks: `visual`, `claim`, `explanation`, `steps`, `source_citation`.
- Visual assets are copied into `output_dir/assets` and referenced from the deck
  output instead of interpolating arbitrary absolute paths into LaTeX.

Validation:

- `uv run pytest tests/test_render.py tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`

## Ticket 2: Agent-Facing Prompt Resources

Goal: expose MCP resources that teach agents how to produce useful rich plans.

Resources to add:

- `academic-slides://prompts/draft_visual_academic_deck`
- `academic-slides://prompts/visual_quality_rubric`
- `academic-slides://prompts/didactic_quality_rubric`
- `academic-slides://schemas/rich_slide_plan`

Acceptance criteria:

- Resources are visible through stdio MCP.
- Prompt text forbids generic bullet-summary decks.
- Prompt text requires source evidence, learning goals, and visual QA.
- Schema text matches the renderer contract.

## Ticket 3: Visual And Didactic Quality Checks

Goal: add a deterministic validator for rich decks and rendered artifacts.

Checks:

- Max one purely textual slide in a short visual deck.
- At least two slides with `visual` blocks when source previews are available.
- Every claim slide includes a source page or artifact reference.
- Slide text length stays within readable limits.
- Rendered previews have non-trivial ink and dimensions.
- Zoom crops exist for dense figures or small text.

Acceptance criteria:

- Validator returns typed errors instead of prose-only review.
- Tests cover a passing deck and clear failures.
- The final agent workflow uses this validator before accepting a deck.

## Ticket 4: End-To-End Visual Deck Agent Run

Goal: have an MCP-only agent generate a 5-7 slide deck from a colorful image
processing chapter using rich layouts.

Acceptance criteria:

- The agent uses only MCP tools.
- The deck compiles and renders all slide previews.
- At least two slides include source visuals.
- Visual artifact list includes source previews, deck previews, and zoom crops.
- The final report states what worked, what failed, and what evidence each slide used.

## Handoff Rules For Future Agents

Start every ticket with:

1. Read `AGENTS.md`.
2. Run `git status --short --branch`.
3. Confirm MCP tool availability when touching MCP.
4. Write or update a failing behavior test before implementation.
5. Keep generated artifacts out of tracked paths.
6. Run the ticket-specific gates plus the repo MCP gates.
7. Commit only explicit scoped files.

If a generated deck compiles but looks like a bullet-summary deck, treat it as
not done.
