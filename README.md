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

The initial MCP surface is implemented in `academic_slides_harness.mcp.server`.
Visual tools generate PNG artifacts with absolute paths, dimensions, DPI, scale,
zoom, and SHA-256 hashes so agents can inspect rendered evidence instead of
guessing from source text.
