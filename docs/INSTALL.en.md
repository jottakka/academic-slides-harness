# Installation

This guide describes a local, no-paid-service setup for Academic Slides Harness.
The project is a Python 3.13 harness and uses `uv` for dependency management and
command execution.

Command surface checked on 2026-05-11 from `pyproject.toml`, CLI help, and MCP
stdio tests.

## Prerequisites

Required:

- Python 3.13.
- `uv`.
- Git.

Recommended:

- Tectonic, for compiling generated Beamer `.tex` files into PDFs.
- Arcade CLI, for local MCP stdio validation.

Optional:

- Ollama, only for tests marked `ollama`. Local LLM output is not a correctness
  dependency.

## Clone And Install

```powershell
git clone <repo-url>
cd academic-slides-harness
uv sync
```

`uv sync` installs the project package and development dependencies declared in
`pyproject.toml`.

## Sanity Checks

Run the normal local checks:

```powershell
uv run academic-slides-harness --help
uv run academic-slides-harness doctor --help
uv run academic-slides-harness doctor models --json
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

Check Arcade readiness before live MCP work:

```powershell
uv run academic-slides-harness doctor arcade --json
```

This checks that an Arcade CLI is available and that the local stdio entrypoint
`server.py` exists. It does not require legacy local HTTP engine or worker ports.

If Arcade is installed somewhere that is not on `PATH`, pass an explicit path:

```powershell
uv run academic-slides-harness doctor arcade --arcade-cli-path <path-to-arcade-executable> --json
```

## MCP Stdio

Start the harness MCP server directly:

```powershell
uv run python server.py stdio
```

If the Arcade CLI is on `PATH`, run the local Arcade stdio wrapper from the
project root:

```powershell
arcade mcp stdio --cwd .
```

If client configuration is missing or stale, generate a VS Code-compatible
Arcade config for your local machine:

```powershell
arcade configure vscode --transport stdio --entrypoint server.py --name academic-slides-harness --config compat\clients\vscode-academic-slides-harness.json
```

Review the generated config before committing it. Some clients write absolute
local paths; tracked examples should stay portable.

Run the live stdio MCP smoke:

```powershell
uv run pytest -m arcade_live -q
```

## Tectonic

Tectonic is required only when compiling generated Beamer source to PDF through
`AcademicSlidesHarness_CompileRenderedBeamer` or tests that compile LaTeX.

The harness looks for Tectonic in this order:

1. `ACADEMIC_SLIDES_TECTONIC_PATH`
2. `TECTONIC_PATH`
3. `tectonic` on `PATH`

PowerShell example:

```powershell
$env:ACADEMIC_SLIDES_TECTONIC_PATH = "<path-to-tectonic-executable>"
uv run pytest tests/test_open_access_book_e2e.py -q
```

If Tectonic is not available, LaTeX compilation tests may skip or compilation
tools may return a typed compile error.

## Windows And PowerShell Notes

- Run commands from the repository root.
- Use PowerShell quoting for pytest markers:

```powershell
uv run pytest -m "not ollama and not arcade_live" -q
```

- If `arcade` is not recognized, either add the Arcade CLI directory to `PATH`
  or use `--arcade-cli-path`.
- Generated artifacts belong in `runs/` or another caller-provided output
  directory. `runs/` is ignored except for `runs/.gitkeep`.
- Do not place tokens, API keys, or private config files in docs or tracked
  generated outputs.

## Troubleshooting

Arcade doctor fails:

- Run `uv run academic-slides-harness doctor arcade --json`.
- Confirm `server.py` exists in the repo root.
- Confirm `arcade` is on `PATH` or pass `--arcade-cli-path`.
- Only use `--check-http-endpoints` when explicitly validating an HTTP setup.

MCP stdio test fails:

- Re-run `uv sync`.
- Run `uv run pytest tests/test_mcp_stdio.py -q` for a narrower stdio check.
- Check whether the failure is a missing dependency, tool registration problem,
  or local process startup error.

Tectonic compile fails:

- Confirm Tectonic is installed or configured through
  `ACADEMIC_SLIDES_TECTONIC_PATH`.
- Re-run only the compilation or E2E test after fixing the executable path.

Secret scan:

```powershell
uv run academic-slides-harness doctor secrets --json
uv run academic-slides-harness doctor secrets --path docs --json
```

Model/provider discovery:

```powershell
uv run academic-slides-harness doctor models --json
```

This reports Ollama, OpenAI/Azure configuration booleans, and MarkItDown
availability without printing API key values.
