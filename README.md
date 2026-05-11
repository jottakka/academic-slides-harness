# Academic Slides Harness

Academic Slides Harness is a Python 3.13, Arcade-first harness for deterministic
academic slide generation. It turns source PDFs into auditable intermediate
artifacts, Beamer source, compiled PDFs, and PNG previews/crops that agents and
humans can inspect.

The project is designed for research and teaching workflows where output must be
repeatable, evidence-backed, and easy to validate. The main runtime surface is a
local MCP server over stdio.

## Status

Implemented:

- PDF ingestion and page text extraction.
- Deterministic v0 Beamer rendering from title/bullet or body slide plans.
- Rich visual Beamer rendering with typed layouts, visual blocks, citations,
  copied assets, image sanitization, and text-density checks.
- Tectonic-backed PDF compilation when Tectonic is available.
- PNG source previews, slide previews, zoom crops, artifact sidecars, dimensions,
  DPI/scale/zoom metadata, SHA-256 hashes, and visual quality warnings.
- Arcade MCP tools/resources over local stdio, with structured outputs and typed
  errors.
- Local diagnostics for Arcade readiness and secret-pattern scans.

Experimental or still maturing:

- Rich visual deck quality validation. Visual artifact warnings exist, but a full
  deterministic deck-quality validator is still planned.
- HTTP transport. The server can run with `http`, but stdio is the documented and
  validated default path.

Planned, not implemented:

- Video ingestion.
- Full public project governance files such as `LICENSE`, `CONTRIBUTING.md`, and
  `SECURITY.md`.

## Quick Start

Prerequisites:

- Python 3.13.
- `uv`.
- Tectonic, if you want to compile Beamer `.tex` files to PDF.
- Arcade CLI, if you want to validate or run the MCP server through Arcade.

From the repository root:

```powershell
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
```

Start the local MCP server:

```powershell
uv run python server.py stdio
```

Run the local Arcade stdio smoke test:

```powershell
uv run pytest -m arcade_live -q
```

If the Arcade CLI is installed and on `PATH`, it can also launch the stdio MCP
server from the project root:

```powershell
arcade mcp stdio --cwd .
```

## Basic MCP Workflow

The primary generation workflow is exposed as MCP tools rather than CLI
subcommands:

1. `AcademicSlidesHarness_CreateRun`
2. `AcademicSlidesHarness_IngestSource`
3. `AcademicSlidesHarness_ExtractSourcePages`
4. `AcademicSlidesHarness_RenderSourcePreview`
5. `AcademicSlidesHarness_RenderZoomCrop`
6. `AcademicSlidesHarness_PlanDeck`
7. `AcademicSlidesHarness_RenderBeamer` or `AcademicSlidesHarness_RenderRichBeamer`
8. `AcademicSlidesHarness_CompileRenderedBeamer`
9. `AcademicSlidesHarness_RenderSlidePreview`
10. `AcademicSlidesHarness_ListVisualArtifacts`
11. `AcademicSlidesHarness_ValidateRun`

Rich visual deck helpers:

- `AcademicSlidesHarness_RenderLayoutPlaceholders`
- `AcademicSlidesHarness_ListThemePresets`
- MCP resources such as `academic-slides://layouts/rich_slide_patterns`,
  `academic-slides://schemas/rich_slide_plan`, and
  `academic-slides://themes/default_visual_academic`

Generated local outputs belong under `runs/` or another caller-provided output
directory. Do not commit generated run artifacts except intentional test
fixtures.

## Architecture Summary

The project keeps deterministic boundaries explicit:

- `core`: Pydantic models, state machines, hashes, and validation contracts.
- `ingest`: PDF inspection and text extraction.
- `render`: Beamer source generation, rich layouts, themes, and Tectonic PDF
  compilation.
- `visualize`: PDF-to-PNG previews, crops, render presets, artifact sidecars, and
  visual quality metrics.
- `llm`: optional local/provider adapters with deterministic fallback behavior.
- `mcp`: Arcade MCP tool registration, resources, structured outputs, and typed
  errors.

See [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md) for the system, tool, and
MCP architecture.

## Documentation

- [Installation guide, English](docs/INSTALL.en.md)
- [Guia de instalacao, pt-BR](docs/INSTALL.pt-BR.md)
- [Usage guide, English](docs/USAGE.en.md)
- [Guia de uso, pt-BR](docs/USAGE.pt-BR.md)
- [Architecture and MCP tools, English](docs/ARCHITECTURE.en.md)
- [Arquitetura e tools MCP, pt-BR](docs/ARCHITECTURE.pt-BR.md)
- [Contributor guide](CONTRIBUTING.md)
- [Public release checklist, English](docs/PUBLIC_RELEASE_CHECKLIST.en.md)
- [Checklist de release publica, pt-BR](docs/PUBLIC_RELEASE_CHECKLIST.pt-BR.md)
- [Foundation architecture notes](docs/design/foundation-architecture.md)
- [Visual rich deck roadmap](docs/design/visual-rich-deck-roadmap.md)
- [Visual quality remediation plan](docs/design/visual-quality-remediation-plan.md)
- [Real source fixture notes](tests/fixtures/sources/README.md)

## Portuguese

Versao em portugues: este README mantem o ingles como idioma principal para
publico open source. A documentacao espelhada em pt-BR esta em:

- [docs/INSTALL.pt-BR.md](docs/INSTALL.pt-BR.md)
- [docs/USAGE.pt-BR.md](docs/USAGE.pt-BR.md)
- [docs/ARCHITECTURE.pt-BR.md](docs/ARCHITECTURE.pt-BR.md)
- [docs/PUBLIC_RELEASE_CHECKLIST.pt-BR.md](docs/PUBLIC_RELEASE_CHECKLIST.pt-BR.md)

## Development Validation

Use these gates before claiming a change is ready:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Optional checks:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run pytest -m ollama -q
uv run academic-slides-harness doctor secrets --json
```

`arcade_live` means a local stdio MCP runtime smoke. It does not require legacy
local HTTP engine or worker ports unless you explicitly run Arcade diagnostics
with `--check-http-endpoints`.

For pull requests, follow [CONTRIBUTING.md](CONTRIBUTING.md) and the repository
PR template. Keep generated artifacts out of tracked paths.
