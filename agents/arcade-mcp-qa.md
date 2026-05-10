# Arcade MCP QA Rules

MCP work must use Arcade-compatible public signatures.

- Tool parameters must use JSON-friendly Python types: `str`, `bool`, `int`, `float`, `dict`, `list`, Pydantic models, or typed dictionaries.
- Tool parameters must use `typing.Annotated` descriptions so Arcade can expose useful schemas.
- Tool functions must have concise docstrings.
- Do not expose `Path` parameters directly in MCP tools; accept strings and convert internally.
- Avoid `from __future__ import annotations` in modules whose functions are registered directly with Arcade, because Arcade inspects runtime annotations.
- Return structured content containing stable machine-readable fields.

For live validation in this repo, prefer the local stdio MCP path:

```powershell
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Here `arcade_live` means local stdio MCP runtime smoke, not HTTP engine/worker
ports by default. Use HTTP checks only when the task explicitly validates an
HTTP setup.

When the task is to test MCP behavior, agents must not create scripts, wrappers,
or direct Python calls as a substitute for calling the MCP tool. If MCP calls are
unavailable or cancelled, stop and report the exact blocker.
