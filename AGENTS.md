# Academic Slides Harness Agent Rules

## Operating Defaults

- Treat this project as an Arcade-first Python 3.13 harness for deterministic academic slide generation.
- Use `uv` for dependency and command execution.
- Keep production code under `src/academic_slides_harness` and tests under `tests`.
- Prefer existing libraries over custom infrastructure: Arcade MCP, Pydantic, transitions, PyMuPDF/pdfplumber, Jinja2, and Tectonic.
- Do not write generated run artifacts into tracked paths except small fixtures intentionally added to tests.

## Required Quality Gates

- Start behavior changes with a failing test and run it before implementation.
- Avoid mocks for internal behavior. Use mocks only for external dependencies that are unavailable, expensive, stateful, or unsafe.
- Prefer real integration evidence for PDF ingestion, Beamer rendering, visual previews, and MCP tool contracts.
- Every MCP-facing tool must return structured content with paths, dimensions, hashes, and typed error data when relevant.
- For any MCP-facing change, docs claim, tool contract change, visual/render tool change, or Arcade/client configuration change, `arcade_live` is mandatory. Configure or verify the Arcade stdio MCP setup, then run the harness as an MCP server through a real stdio MCP client before claiming completion.
- Runtime checks must name the command or tool call used and whether it passed, failed, or was skipped.

## Validation Commands

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json` before live MCP work.
- `arcade configure vscode --transport stdio --entrypoint server.py --name academic-slides-harness --config compat\clients\vscode-academic-slides-harness.json` when the local client config is missing, stale, or MCP setup changed.
- `uv run pytest -m arcade_live -q` for every MCP-facing change. In this repo, `arcade_live` means local stdio MCP runtime smoke, not engine/worker HTTP endpoints.
- `uv run pytest -m ollama -q` when local Ollama is expected to participate.
- Use `--check-http-endpoints` or HTTP transport checks only when explicitly validating an HTTP setup.

## Visual Artifact Policy

- Visual tools must write PNG screenshots or crops to a caller-provided output directory.
- Visual tool responses must include absolute paths, width, height, DPI, scale, zoom, target, page/slide number, and SHA-256 hash.
- Use `fast` previews for iteration, `review` for normal QA, and `print` only when high resolution is needed.
- For detailed QA, generate zoom crops instead of relying only on full-slide screenshots.

## LLM Policy

- Local LLMs are optional acceleration, not correctness dependencies.
- If Ollama is unavailable or disabled, use deterministic fallback providers and report that fallback explicitly.
- Do not let LLM output bypass deterministic validation, LaTeX compilation, screenshot generation, or MCP contract checks.
