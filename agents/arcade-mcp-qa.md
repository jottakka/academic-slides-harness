# Arcade MCP QA Rules

MCP work must use Arcade-compatible public signatures.

- Tool parameters must use JSON-friendly Python types: `str`, `bool`, `int`, `float`, `dict`, `list`, Pydantic models, or typed dictionaries.
- Tool parameters must use `typing.Annotated` descriptions so Arcade can expose useful schemas.
- Tool functions must have concise docstrings.
- Do not expose `Path` parameters directly in MCP tools; accept strings and convert internally.
- Avoid `from __future__ import annotations` in modules whose functions are registered directly with Arcade, because Arcade inspects runtime annotations.
- Return structured content containing stable machine-readable fields.

For live validation, use a real Arcade engine and worker. If unavailable, run in-process app registration and direct tool contract tests, then label live validation as skipped.
