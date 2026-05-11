# Public Release Checklist

Use this checklist before making the repository public or inviting outside
contributors. It separates what is already true from what is still pending.

Checked on 2026-05-11 against the current repository tree.

## Repository Basics

- [x] Public-facing README explains the project, status, quick start, MCP usage,
  validation commands, docs map, and generated artifact policy.
- [ ] `LICENSE` is present.
- [ ] `CONTRIBUTING.md` is present.
- [ ] `SECURITY.md` is present.
- [ ] `CODE_OF_CONDUCT.md` is present if the project wants community governance
  expectations before public collaboration.
- [ ] Issue templates are present.
- [ ] Pull request template is present.

## Safety And Secrets

- [x] `.gitignore` excludes generated runs and common Python/LaTeX/editor
  artifacts.
- [x] Docs avoid raw tokens and API keys.
- [x] Public docs use placeholders for private local executable paths.
- [x] `uv run academic-slides-harness doctor secrets --json` passed in the
  2026-05-11 readiness pass. Re-run before final release.
- [ ] Review `compat/clients/` for accidental local user paths or credentials
  before publishing.

## Installation And Usage

- [x] Python 3.13 and `uv` are documented.
- [x] Tectonic is documented as required for PDF compilation.
- [x] Arcade CLI is documented as required for Arcade stdio validation.
- [x] MCP stdio entrypoint is documented:
  `uv run python server.py stdio`.
- [x] Local Arcade runner is documented without private paths:
  `arcade mcp stdio --cwd .`.
- [x] Windows/PowerShell troubleshooting is documented.

## Implemented Status

- [x] Implemented features are separated from experimental and planned features.
- [x] Video ingestion is marked planned, not implemented.
- [x] HTTP transport is marked optional/experimental, not the default live path.
- [x] Rich visual deck validation is described as maturing, not complete.
- [x] `arcade_live` is documented as local stdio MCP smoke.

## Tests And Validation

Before release, run and record:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Recommended additional checks:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run academic-slides-harness doctor secrets --json
```

Run `uv run pytest -m ollama -q` only when local Ollama participation is
expected.

Latest readiness pass, 2026-05-11:

- `uv run ruff format --check .`: passed.
- `uv run ruff check .`: passed.
- `uv run pytest -m "not ollama and not arcade_live" -q`: passed, 123 passed
  and 2 deselected.
- `uv run academic-slides-harness doctor arcade --json`: passed.
- `uv run pytest -m arcade_live -q`: passed, 1 passed and 124 deselected.
- `uv run academic-slides-harness doctor secrets --json`: passed.

## Known Limitations To Keep Public

- The CLI is diagnostic-only for now. Generation is MCP-first.
- Rich visual rendering exists, but deterministic deck-level quality validation
  is still planned.
- Tectonic must be installed or configured to compile PDFs.
- Generated runs should not be committed.
- Public release still needs licensing and contribution governance decisions.

## Roadmap Clarity

- [x] Current design docs identify rich visual deck work.
- [x] Visual remediation plan documents recent quality work and the next
  validator need.
- [ ] Collapse stale roadmap wording before a major public announcement if the
  repo should look polished beyond MVP readiness.
