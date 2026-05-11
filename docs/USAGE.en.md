# Usage

Academic Slides Harness is used primarily through MCP tools. The CLI is currently
for diagnostics, while generation, rendering, previewing, and validation happen
through the local MCP server.

## Start The MCP Server

```powershell
uv run python server.py stdio
```

Any MCP client that supports stdio can connect to this process. Arcade can also
run the server from the repository root:

```powershell
arcade mcp stdio --cwd .
```

## Model Provider Discovery

Before choosing a deterministic or model-assisted path, inspect local/configured
providers without exposing secrets:

```json
{
  "tool": "AcademicSlidesHarness_ListModelProviders",
  "arguments": {}
}
```

The response reports Ollama availability and model names, OpenAI/Azure
configuration booleans, and MarkItDown package availability. It never prints API
key values.

## Basic Tool Flow

Use a caller-provided output directory, usually under `runs/`.

1. Create a run:

```json
{
  "tool": "AcademicSlidesHarness_CreateRun",
  "arguments": {
    "base_dir": "runs",
    "title": "Image Processing Chapter 12"
  }
}
```

2. Inspect the source PDF:

```json
{
  "tool": "AcademicSlidesHarness_IngestSource",
  "arguments": {
    "source_path": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf"
  }
}
```

3. Extract page text for planning:

```json
{
  "tool": "AcademicSlidesHarness_ExtractSourcePages",
  "arguments": {
    "source_pdf": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "pages": "1,3,5",
    "max_chars_per_page": 2000
  }
}
```

4. Render source previews:

```json
{
  "tool": "AcademicSlidesHarness_RenderSourcePreview",
  "arguments": {
    "source_pdf": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "pages": "1,4",
    "resolution": "review"
  }
}
```

5. Render a focused source crop:

```json
{
  "tool": "AcademicSlidesHarness_RenderZoomCrop",
  "arguments": {
    "pdf_path": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "target": "source_pdf",
    "page": 4,
    "crop": {
      "x": 0.05,
      "y": 0.42,
      "width": 0.9,
      "height": 0.36,
      "normalized": true
    },
    "resolution": "review",
    "zoom": 2.5
  }
}
```

6. Create a deterministic draft plan:

```json
{
  "tool": "AcademicSlidesHarness_PlanDeck",
  "arguments": {
    "title": "Image Processing Chapter 12",
    "excerpts": ["<page excerpt 1>", "<page excerpt 3>", "<page excerpt 5>"],
    "max_slides": 3
  }
}
```

7. Render a compatibility Beamer deck:

```json
{
  "tool": "AcademicSlidesHarness_RenderBeamer",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/rendered",
    "title": "Image Processing Chapter 12",
    "slides": [
      {
        "title": "Image Processing",
        "bullets": ["Images become matrices", "Operations should be reproducible"]
      }
    ]
  }
}
```

For the richer visual path, prefer `AcademicSlidesHarness_RenderRichBeamer`.

## Rich Visual Deck Workflow

First inspect the available visual layouts and theme:

```json
{ "tool": "AcademicSlidesHarness_ListThemePresets", "arguments": {} }
```

Read these MCP resources from your client:

- `academic-slides://layouts/rich_slide_patterns`
- `academic-slides://schemas/rich_slide_plan`
- `academic-slides://prompts/draft_visual_academic_deck`
- `academic-slides://prompts/visual_quality_rubric`
- `academic-slides://prompts/didactic_quality_rubric`
- `academic-slides://themes/default_visual_academic`
- `academic-slides://themes/unb_visual_academic`

Use `equation_explanation` with `latex_equation` for formulas that can be
transcribed faithfully. Use `table_explanation` with `latex_table` for compact
source tables. Keep `RenderZoomCrop` for diagrams, plots, handwritten
derivations, and source-specific visual evidence.

Optionally render layout placeholders:

```json
{
  "tool": "AcademicSlidesHarness_RenderLayoutPlaceholders",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/layout-placeholders",
    "layouts": "all",
    "overwrite": false
  }
}
```

Render rich Beamer source:

```json
{
  "tool": "AcademicSlidesHarness_RenderRichBeamer",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/rich-rendered",
    "title": "Image Processing Chapter 12",
    "slides": [
      {
        "title": "Pixels Become Measurements",
        "layout": "figure_explanation",
        "learning_goal": "Explain why a focused crop is better than a full page screenshot.",
        "blocks": [
          {
            "type": "visual",
            "artifact_path": "<absolute-path-to-source-crop-png>"
          },
          {
            "type": "claim",
            "text": "Focused visual evidence keeps the teaching point inspectable."
          },
          {
            "type": "source_citation",
            "source_page": 4
          }
        ]
      }
    ]
  }
}
```

The rich renderer copies visual assets into the deck output directory, sanitizes
images, checks text limits, and rejects hard visual warnings unless the slide
explicitly allows an override.

## Compile And Preview

Compile generated Beamer source with Tectonic:

```json
{
  "tool": "AcademicSlidesHarness_CompileRenderedBeamer",
  "arguments": {
    "tex_path": "runs/image-processing-chapter-12/rich-rendered/deck.tex",
    "output_dir": "runs/image-processing-chapter-12/compiled"
  }
}
```

Render slide previews:

```json
{
  "tool": "AcademicSlidesHarness_RenderSlidePreview",
  "arguments": {
    "deck_pdf": "runs/image-processing-chapter-12/compiled/deck.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "slides": "1-3",
    "resolution": "review"
  }
}
```

List artifacts:

```json
{
  "tool": "AcademicSlidesHarness_ListVisualArtifacts",
  "arguments": {
    "screenshots_dir": "runs/image-processing-chapter-12/screenshots"
  }
}
```

Validate the run:

```json
{
  "tool": "AcademicSlidesHarness_ValidateRun",
  "arguments": {
    "run_dir": "runs/image-processing-chapter-12"
  }
}
```

## Outputs In `runs/`

Typical run outputs:

- `manifest.json`: run identity and metadata.
- `screenshots/`: source previews, deck previews, zoom crops, and `.png.json`
  metadata sidecars.
- `rendered/` or `rich-rendered/`: generated `deck.tex` and copied visual assets.
- `compiled/`: generated `deck.pdf` when Tectonic succeeds.

`runs/` is ignored by git except for `runs/.gitkeep`.

## Real Fixture

The repository includes a real open-access image-processing chapter fixture:

```text
tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf
```

It is used by end-to-end tests because it contains realistic academic prose,
figures, formulas, and tables. See `tests/fixtures/sources/README.md`.

## Visual QA

Visual tools return structured metadata with absolute paths, dimensions,
resolution, DPI, scale, zoom, target, page/slide number, SHA-256 hashes, and
quality warnings. For dense figures or text, prefer zoom crops over only
full-slide previews.

Resolution presets:

- `fast`: iteration.
- `review`: normal QA.
- `print`: high resolution when needed.

## Validation

Normal validation:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Optional:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run pytest -m ollama -q
```
