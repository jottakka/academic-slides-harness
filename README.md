# Academic Slides Harness

Provider-neutral harness for generating academic slide decks from source material.

## Goal

Build a deterministic LaTeX-first pipeline that turns PDFs, books, and later videos into Beamer decks with auditable intermediate artifacts.

## V1 Direction

- PDF/books first.
- Beamer `.tex` as the primary editable output.
- Deterministic ingestion, layout, rendering, validation, and slide preview generation.
- Agent-facing MCP tools through Arcade MCP, including baseline polling and advanced MCP features such as tasks, progress, elicitation, resources, prompts, structured output, and typed errors.

## Initial Structure

- `src/`: Python harness source.
- `tests/`: unit and integration tests.
- `templates/beamer/`: reusable LaTeX/Beamer themes, layouts, and macros.
- `agents/`: agent prompts, rules, and handoff documents.
- `compat/clients/`: client-specific MCP configs and smoke tests.
- `docs/`: design and implementation notes.
- `runs/`: generated local runs and artifacts.

## Development

Use `uv` from the repository root:

```powershell
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

## Local Diagnostics

Use the Arcade doctor before live MCP work:

```powershell
uv run academic-slides-harness doctor arcade
uv run academic-slides-harness doctor arcade --json
```

The command checks the Arcade CLI and this repo's local stdio MCP entrypoint.
Arcade MCP can run locally with stdio; local engine and worker ports are not
required for the default live path. Use `--check-http-endpoints` only when
explicitly validating an HTTP setup.

Use the secret doctor before sharing local Arcade configs or repro bundles:

```powershell
uv run academic-slides-harness doctor secrets
uv run academic-slides-harness doctor secrets --path C:\Users\fjlim\OneDrive\Documents\arcade-ai\engine.yaml --json
```

The secret scan reports file paths, line numbers, and finding types without
printing matched secret values.

The initial MCP surface is implemented in `academic_slides_harness.mcp.server`.
Visual tools generate PNG artifacts with absolute paths, dimensions, DPI, scale,
zoom, and SHA-256 hashes so agents can inspect rendered evidence instead of
guessing from source text.
Visual preview and crop tools refuse to overwrite an existing PNG by default and
return a typed `artifact_exists` error through MCP. Pass `overwrite=true` only
when replacing a previous artifact is intentional.

## MCP Stdio

The root `server.py` runs the Arcade MCP app with stdio by default:

```powershell
uv run python server.py stdio
```

Arcade CLI can generate client config for this entrypoint:

```powershell
C:\Users\fjlim\.local\bin\arcade.exe configure vscode --transport stdio --entrypoint server.py --name academic-slides-harness --config compat\clients\vscode-academic-slides-harness.json
```

The Arcade CLI also exposes a local MCP runner:

```powershell
C:\Users\fjlim\.local\bin\arcade.exe mcp stdio --cwd .
```
