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

Status: implemented with a layout catalog and placeholder preview tool.

Implemented contract:

- MCP resources:
  - `academic-slides://layouts/rich_slide_patterns`
  - `academic-slides://schemas/rich_slide_plan`
  - `academic-slides://prompts/draft_visual_academic_deck`
  - `academic-slides://prompts/visual_quality_rubric`
  - `academic-slides://prompts/didactic_quality_rubric`
- MCP tool: `RenderLayoutPlaceholders`.
- Placeholder PNGs are written to a caller-provided output directory and include
  absolute paths, dimensions, format, hash, layout name, required blocks, and
  suggested text limits.

Acceptance criteria:

- Resources are visible through stdio MCP.
- Prompt text forbids generic bullet-summary decks.
- Prompt text requires source evidence, learning goals, and visual QA.
- Schema text matches the renderer contract.

Validation:

- `uv run pytest tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`

## Ticket 3: Rich Plan Text Limits

Goal: prevent overflow before render by checking text density in the rich plan.

Checks:

- Max title length per layout.
- Max learning-goal length per layout.
- Max claim and explanation length per layout.
- Max step count and per-step length for `workflow_steps`.
- Actionable typed errors that tell the agent which slide/block to shorten.

Acceptance criteria:

- Validator returns typed `text_overflow_risk` errors.
- Tests cover title overflow, claim overflow, explanation overflow, too many
  steps, and a passing compact deck.
- `RenderRichBeamer` or a dedicated validation tool can report the problem
  before LaTeX compilation.

## Ticket 4: Image Sanitization Before Embed

Goal: make visual assets safe and predictable before `RenderRichBeamer` copies
them into the deck.

Checks:

- Input path exists and is a readable image.
- Image format is PNG/JPEG or convertible to PNG.
- Image mode is normalized to RGB/RGBA when needed.
- Minimum dimensions are enforced for slide use.
- Sanitized output records absolute path, width, height, format, hash, source
  path, and whether conversion was performed.

Acceptance criteria:

- Valid PNG/JPEG assets pass unchanged or with a clearly reported conversion.
- Corrupt images return typed `invalid_visual_artifact`.
- Tiny images return typed `image_too_small`.
- The rich renderer uses sanitized metadata instead of blindly copying images.

## Ticket 5: Image Legibility And Crop Quality

Goal: judge whether a chosen source preview/crop is usable on a slide.

Checks:

- Dimensions and aspect ratio fit the selected layout.
- Basic contrast/ink metrics warn on nearly blank or low-contrast images.
- Crops with too much embedded PDF text are flagged for tighter crop selection.
- Low-quality findings are warnings at first, except unreadable/corrupt images.

Acceptance criteria:

- Synthetic blank, low-contrast, tiny, and normal images produce distinct
  structured results.
- Real source-preview artifacts include quality warnings in their metadata.
- Agent-facing prompts require replacing or cropping images with hard warnings.

## Ticket 6: Visual And Didactic Quality Checks

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

## Ticket 7: End-To-End Visual Deck Agent Run

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
