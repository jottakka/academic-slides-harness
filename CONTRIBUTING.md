# Contributing

Thanks for considering a contribution to Academic Slides Harness. This project is
an Arcade-first Python 3.13 harness for deterministic academic slide generation.
The main public runtime surface is MCP over local stdio.

## Start Here

1. Read `README.md`, `docs/INSTALL.en.md`, `docs/USAGE.en.md`, and
   `docs/ARCHITECTURE.en.md`.
2. Install dependencies with `uv sync`.
3. Run the normal local gate before opening a pull request:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

If your change touches MCP tools, MCP resources, render contracts, visual
artifacts, Arcade/client configuration, or docs that claim MCP behavior, also
run:

```powershell
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

`arcade_live` means local stdio MCP runtime smoke. It is not an HTTP engine or
worker check.

## Scope And Artifacts

- Keep production code under `src/academic_slides_harness`.
- Keep tests under `tests`.
- Use `uv` for project commands.
- Do not commit generated run artifacts. Use `runs/` or a temporary directory
  for local outputs.
- Keep public docs free of tokens, private paths, local usernames, and private
  config values.
- Use `uv run academic-slides-harness doctor secrets --json` before public
  release or when changing docs/config examples.

## Testing Expectations

Behavior-changing code should start with a useful failing test. Prefer real
integration boundaries when practical: real PDFs, real Tectonic when available,
real stdio MCP calls for MCP-facing changes, and rendered PNG evidence for visual
work.

Avoid mocks for internal behavior. Mock only external, slow, stateful,
nondeterministic, unavailable, or unsafe boundaries.

## MCP And Visual Work

MCP tools should:

- expose JSON-friendly parameters;
- avoid `Path` parameters at the tool boundary;
- use `typing.Annotated` parameter descriptions;
- return structured content with stable machine-readable fields;
- return typed errors for recoverable failures;
- include absolute paths, dimensions, render options, page/slide numbers, and
  SHA-256 hashes for visual artifacts.

Visual changes are not done until rendered evidence exists. For dense slides or
figures, generate zoom crops rather than relying only on full-slide previews.

## Pull Request Standard

Every pull request should include:

- a clear summary of what changed;
- implemented vs experimental vs planned status when docs mention capability;
- exact validation commands and pass/fail/skip results;
- notes about generated artifacts, if any;
- screenshots or artifact paths for visual/render changes;
- residual risks or known limitations.

Use `.github/PULL_REQUEST_TEMPLATE.md` when opening a PR.
