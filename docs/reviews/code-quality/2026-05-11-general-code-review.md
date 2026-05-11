# General Code Review - 2026-05-11

## Scope

Three read-only agents reviewed the repository:

- public-readiness path scan for personal/local environment references;
- core, ingest, render, LLM, and CLI review;
- MCP, visual artifact, stdio, Arcade, and contract review.

The path cleanup was implemented separately in this branch. The code findings
below are not all fixed yet; treat them as the next improvement backlog.

## Environment Path Audit

Personal environment references removed or avoided:

- no tracked hits remain for local user profile paths, local usernames,
  cloud-sync folders, operating-system app-data folders, tool cache paths, or
  local Arcade install paths;
- docs now use placeholders such as `<path-to-arcade-executable>`,
  `<path-to-tectonic-executable>`, and `<absolute-path-to-source-crop-png>`;
- `doctor arcade` no longer probes a home-directory Arcade install path
  implicitly;
- Tectonic discovery no longer probes a home-directory tool cache implicitly.

Portability cleanup:

- `src/academic_slides_harness/render/layout_catalog.py` now probes fonts by
  logical font name with `ImageFont.load_default()` as fallback, rather than
  embedding operating-system font paths.

## Findings

### P1: Tectonic timeouts are reported as `compile_failed`

`compile_tex_with_tectonic()` converts `subprocess.TimeoutExpired` into a
`RuntimeError`, while the MCP wrapper catches `TimeoutError` to return
`compile_timeout`. The actual subprocess-timeout path can therefore surface as
`compile_failed`.

Suggested fix:

- introduce a timeout-specific exception type, or raise `TimeoutError` from the
  Tectonic wrapper;
- update the MCP contract test to exercise the real `subprocess.TimeoutExpired`
  path.

Suggested validation:

```powershell
uv run pytest tests/test_render.py tests/test_mcp_contracts.py -q -k "timeout or compile"
```

### P1: Duplicate `CreateRun` titles overwrite the manifest

`CreateRun` derives the run directory from the title slug and uses `exist_ok`,
then writes `manifest.json`. Calling it twice with the same title can replace
the manifest while old artifacts remain in the same directory.

Suggested fix:

- return a typed `run_exists` error unless `overwrite` is explicitly requested;
  or
- generate a unique run directory when the slug already exists.

Suggested validation:

```powershell
uv run pytest tests/test_mcp_contracts.py -q -k create_run
```

### P2: `ListVisualArtifacts` can crash on corrupt visual files or sidecars

The tool maps every PNG through metadata extraction. Corrupt PNGs or malformed
`.png.json` sidecars can raise lower-level exceptions instead of returning typed
MCP errors.

Suggested fix:

- return `invalid_visual_artifact` for unreadable PNGs;
- return `invalid_visual_metadata` for malformed sidecars;
- preserve the offending relative path in error details.

Suggested validation:

```powershell
uv run pytest tests/test_mcp_contracts.py -q -k visual_artifacts
```

### P2: Out-of-range preview and crop requests use generic errors

Low-level visual validation raises `ValueError` for out-of-range pages and crops,
but MCP wrappers currently collapse these into generic `preview_failed` or
`crop_failed` errors.

Suggested fix:

- map out-of-range page selection to `invalid_page_selection`;
- map invalid crop bounds to `invalid_crop`.

Suggested validation:

```powershell
uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q -k "page or crop"
```

### P2: Visual artifact metadata omits the requested preset name

The public contract says visual responses include render preset information, but
artifact structured content currently exposes DPI, scale, and zoom without the
original preset name (`fast`, `review`, or `print`).

Suggested fix:

- include the preset name in `resolution`, or add a separate stable
  `resolution_preset` field.

Suggested validation:

```powershell
uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q -k resolution
```

### P2: Malformed Ollama embeddings can leak raw conversion errors

`OllamaProvider.embed()` wraps HTTP and JSON failures, but conversion of returned
embedding values to floats can still raise raw `ValueError` on malformed payloads.

Suggested fix:

- include embedding validation/conversion inside the existing error wrapper;
- raise a clear fallback-friendly `RuntimeError`.

Suggested validation:

```powershell
uv run pytest tests/test_llm.py -q -k ollama
```

### P2: `max_slides <= 0` silently produces one slide

The MCP contract describes `max_slides` as a maximum, but invalid values are
coerced to one slide by the deterministic fallback provider.

Suggested fix:

- validate `max_slides >= 1` at the MCP boundary and return typed
  `invalid_options`;
- add provider-level validation or document provider coercion explicitly.

Suggested validation:

```powershell
uv run pytest tests/test_llm.py tests/test_mcp_contracts.py -q -k max_slides
```

## Recommended Ticket Order

1. Fix Tectonic timeout typing because it affects MCP error reliability.
2. Decide `CreateRun` duplicate-title semantics before external users rely on
   stable run paths.
3. Harden visual artifact listing and preview/crop typed errors together.
4. Add resolution preset metadata to visual artifacts.
5. Harden Ollama malformed payload fallback.
6. Validate `max_slides` at the MCP boundary.

## Review Validation Evidence

Reviewer-reported checks:

- MCP/visual reviewer: `uv run pytest tests/test_mcp_contracts.py
  tests/test_mcp_stdio.py tests/test_arcade_live.py tests/test_visualize.py
  tests/test_visual_quality.py -q` passed with 86 tests.
- MCP/visual reviewer: `uv run ruff check src tests` passed.
- MCP/visual reviewer: `uv run academic-slides-harness doctor arcade --json`
  passed.
- MCP/visual reviewer: `uv run pytest -m arcade_live -q` passed.

Coordinator revalidation for the path cleanup is recorded in the final branch
commit and release checklist.
