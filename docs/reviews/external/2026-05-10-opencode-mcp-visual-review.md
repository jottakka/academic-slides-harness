# OpenCode MCP and Visual Review - 2026-05-10

## Scope

### Files Inspected
- `src/academic_slides_harness/mcp/server.py` (540 lines)
- `src/academic_slides_harness/visualize/options.py` (87 lines)
- `src/academic_slides_harness/visualize/preview.py` (101 lines)
- `src/academic_slides_harness/render/beamer.py` (60 lines)
- `src/academic_slides_harness/render/tectonic.py` (53 lines)
- `src/academic_slides_harness/core/models.py` (160 lines)
- `tests/test_mcp_contracts.py` (303 lines)
- `tests/test_mcp_stdio.py` (42 lines)
- `tests/test_arcade_live.py` (109 lines)
- `tests/test_visualize.py` (89 lines)
- `tests/test_mcp_vertical_slice.py` (109 lines)
- `README.md` (84 lines)
- `docs/design/foundation-architecture.md` (32 lines)
- `agents/arcade-mcp-qa.md` (12 lines)
- `agents/beamer-visual-qa.md` (12 lines)

### Commands Run
```
uv run pytest tests/test_mcp_contracts.py -v -q        # 21 passed
uv run pytest tests/test_visualize.py -v -q            # 12 passed
uv run pytest tests/test_mcp_vertical_slice.py -v -q   # 1 passed
uv run pytest tests/test_mcp_stdio.py -v -q            # 1 passed
uv run pytest tests/test_arcade_live.py -v -q          # 1 passed
uv run ruff check .                                    # All checks passed
uv run ruff format --check .                           # 30 files already formatted
```

## Findings

### P1: Duplicate import block in `server.py`
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 17-23
- **Evidence:**
  ```python
  from academic_slides_harness.visualize.preview import (
      render_pdf_pages,
  )
  from academic_slides_harness.visualize.preview import (
      render_zoom_crop as render_crop,
  )
  ```
  These two imports from the same module are split into separate statements for no apparent reason.
- **Impact:** Minor code smell; suggests incomplete refactoring. Could confuse future maintainers.
- **Recommendation:** Merge into a single import block.
- **Confidence:** high

### P1: `_exception_result` strips structured error information
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 524-529
- **Evidence:**
  ```python
  def _exception_result(*, kind: str, exc: Exception) -> ToolResult:
      return ToolResult.error(
          kind=kind,
          message=str(exc),
          details={"exception_type": exc.__class__.__name__},
      )
  ```
  For `ValidationError`, `str(exc)` produces a multi-line human-readable string unsuitable for machine parsing. For `fitz` exceptions, the message may not include the offending path or page number.
- **Impact:** Agents consuming MCP structured output cannot programmatically distinguish between, e.g., a missing file and a corrupt PDF. Debugging requires server-side log access.
- **Recommendation:** Add helper to extract structured fields from common exception types (e.g., `ValidationError.errors()`, `fitz.FileDataError` path info).
- **Confidence:** high

### P1: `render_beamer` does not validate `slides` is a list
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 104-121
- **Evidence:**
  ```python
  for index, slide in enumerate(slides, start=1):
      if "title" not in slide:
  ```
  If `slides` is a string (e.g., passed by a confused agent), `enumerate("abc")` yields characters, and `"title" not in "a"` is checked, producing a nonsensical error message.
- **Impact:** Poor developer experience; error message will say "Slide 1 must include title" for a string character.
- **Recommendation:** Add `if not isinstance(slides, list): return ToolResult.error(kind="invalid_slides", ...)` before the loop.
- **Confidence:** high

### P1: `parse_page_selection` does not validate against PDF page count
- **Area:** `src/academic_slides_harness/visualize/options.py`, lines 61-78
- **Evidence:** The function validates that pages are positive integers but has no knowledge of the actual PDF page count. `render_pdf_pages` only catches the generic `fitz` exception.
- **Impact:** Agents requesting page 100 of a 10-page PDF get `preview_failed` with a low-level fitz error instead of a structured `invalid_page_selection` error.
- **Recommendation:** Move page-count validation into `render_pdf_pages` / `render_zoom_crop` and return a specific error kind.
- **Confidence:** high

### P1: `render_pdf_pages` and `render_zoom_crop` do not pre-validate PDF existence
- **Area:** `src/academic_slides_harness/visualize/preview.py`, lines 25, 61
- **Evidence:** Both functions call `fitz.open(pdf_path)` directly. A missing file raises a generic `fitz.FileNotDataError` or `FileNotFoundError` caught only by the broad `except Exception` in the MCP tool wrappers.
- **Impact:** Agents receive `preview_failed` or `crop_failed` instead of a clear `missing_input` error.
- **Recommendation:** Add explicit `if not pdf_path.is_file(): raise FileNotFoundError(...)` before `fitz.open`, or check in the MCP wrapper and return `ToolResult.error(kind="missing_input", ...)`.
- **Confidence:** high

### P1: `compile_tex_with_tectonic` lacks subprocess timeout
- **Area:** `src/academic_slides_harness/render/tectonic.py`, lines 41-47
- **Evidence:**
  ```python
  completed = subprocess.run(
      command,
      cwd=tex_path.parent,
      check=False,
      capture_output=True,
      text=True,
  )
  ```
  No `timeout` parameter is passed.
- **Impact:** A hung Tectonic process (e.g., waiting for network package download) can block the MCP server indefinitely.
- **Recommendation:** Add `timeout=300` (5 minutes) or make it configurable via environment variable.
- **Confidence:** high

### P2: Duplicated render-options parsing in MCP tools
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 176-183, 212-219
- **Evidence:** `render_source_preview` and `render_slide_preview` contain identical `try/except` blocks for `_parse_render_options`.
- **Impact:** Violation of DRY; increases maintenance burden when adding new resolution presets or validation rules.
- **Recommendation:** Extract a helper `_parse_render_options_safe(resolution, dpi, scale, zoom=1.0) -> ToolResult | RenderOptions` that returns a `ToolResult.error` on failure.
- **Confidence:** high

### P2: `_png_metadata` reads file twice
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 376-393
- **Evidence:**
  ```python
  with Image.open(path) as image:
      width, height = image.size
  sha256_bytes(path.read_bytes())
  ```
  The file is opened once by Pillow and then read entirely into memory for the hash.
- **Impact:** For large print-resolution PNGs (e.g., 300 DPI of a complex academic slide), this doubles I/O and memory pressure.
- **Recommendation:** Stream-read the file once for hashing, or use `image.tobytes()` if the raw pixel hash is acceptable.
- **Confidence:** high

### P2: `ScreenshotArtifact.from_file` reads file twice
- **Area:** `src/academic_slides_harness/core/models.py`, lines 62-87
- **Evidence:**
  ```python
  resolved = path.resolve()
  return cls(
      artifact_id=f"{target}-p{page}-{sha256_bytes(resolved.read_bytes())[:12]}",
      ...
      sha256=sha256_bytes(resolved.read_bytes()),
  )
  ```
  `resolved.read_bytes()` is called twice.
- **Impact:** Same as above - unnecessary I/O duplication for every rendered artifact.
- **Recommendation:** Read once, store in a local variable, and reuse.
- **Confidence:** high

### P2: `_validate_manifest_file` parses JSON twice
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 465-487
- **Evidence:**
  ```python
  raw_manifest = manifest_path.read_text(encoding="utf-8")
  try:
      json.loads(raw_manifest)
  ...
  manifest = RunManifest.model_validate_json(raw_manifest)
  ```
  `json.loads` is used only to distinguish parse errors from schema errors, but `model_validate_json` would raise a different exception for both.
- **Impact:** Minor inefficiency; for large manifests, unnecessary CPU work.
- **Recommendation:** Catch `ValidationError` from `model_validate_json` and inspect whether its cause is `JSONDecodeError`.
- **Confidence:** medium

### P2: `list_visual_artifacts` uses recursive glob without depth limit
- **Area:** `src/academic_slides_harness/mcp/server.py`, line 297
- **Evidence:** `png_paths = sorted(directory.rglob("*.png")) if directory.exists() else []`
- **Impact:** If a run directory accumulates many nested files over time, `rglob` traversal could become slow and memory-intensive.
- **Recommendation:** Use `directory.glob("*.png")` (non-recursive) or limit recursion depth, since screenshots are expected to be flat under `screenshots/`.
- **Confidence:** medium

### P2: `ingest_source` does not validate `source_path` is a file
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 66-80
- **Evidence:** `if not Path(source_path).exists():` - a directory would pass this check and then fail inside `inspect_pdf` with an unclear error.
- **Impact:** Agents passing a directory path receive `ingest_failed` instead of `missing_input` or `not_a_file`.
- **Recommendation:** Change to `if not Path(source_path).is_file():`.
- **Confidence:** high

### P2: `create_run` does not validate `base_dir` is a directory
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 40-63
- **Evidence:** `run_dir = Path(base_dir).resolve() / slug` followed by `run_dir.mkdir(parents=True, exist_ok=True)`. If `base_dir` is an existing file, `mkdir` raises `NotADirectoryError`.
- **Impact:** Confusing error for agents; not wrapped in a structured `ToolResult.error`.
- **Recommendation:** Add explicit check `if Path(base_dir).exists() and not Path(base_dir).is_dir(): return ToolResult.error(kind="invalid_base_dir", ...)`.
- **Confidence:** medium

### P2: `render_zoom_crop` does not validate crop bounds against page rect
- **Area:** `src/academic_slides_harness/visualize/preview.py`, lines 86-93
- **Evidence:** `_resolve_crop` converts normalized coordinates to absolute but does not clamp or validate that the resulting rect is within `page_rect`.
- **Impact:** Agents can request crops outside the page; `fitz` may return an empty pixmap or raise an exception.
- **Recommendation:** Clamp crop coordinates to `page_rect` or return a structured error if the crop is entirely outside.
- **Confidence:** medium

### P2: `MCP_TOOL_NAMES` ordering inconsistent with `build_app`
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 24-37, 328-341
- **Evidence:** `MCP_TOOL_NAMES` is a `frozenset` (unordered) containing `compile_rendered_beamer` first, but `build_app` appends it last.
- **Impact:** No functional bug, but the test `test_mcp_tool_registry_contains_initial_contract` relies on set equality, masking ordering issues that could matter for documentation or UI presentation.
- **Recommendation:** Make `MCP_TOOL_NAMES` a `tuple` to enforce stable ordering, and assert ordering in tests.
- **Confidence:** low

### P2: `build_app` registers tools but does not expose them via HTTP transport
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 364-369
- **Evidence:** `main()` accepts `"stdio"` or `"http"` but `build_app().run(transport=transport)` is passed directly. No HTTP server configuration (host, port, CORS) is exposed.
- **Impact:** Running `server.py http` may fail or bind to unexpected defaults, making HTTP-based agent integration unreliable.
- **Recommendation:** Document HTTP transport behavior in README, or expose `--host` and `--port` CLI arguments.
- **Confidence:** medium

### P2: `render_beamer` does not validate LaTeX special characters in slide dict before passing to renderer
- **Area:** `src/academic_slides_harness/mcp/server.py`, lines 104-121
- **Evidence:** `render_beamer_tex` does call `_escape_latex`, but if an agent passes a non-string `title` (e.g., `int` or `dict`), `_escape_latex` receives it via `str(slide["title"])` which may produce unexpected output.
- **Impact:** Type coercion could silently produce malformed LaTeX.
- **Recommendation:** Validate that `slide["title"]` and bullet items are strings before rendering.
- **Confidence:** medium

## Performance Notes

1. **Repeated PDF opens:** `render_pdf_pages` and `render_zoom_crop` each open the PDF independently. An agent generating previews and crops for the same source will pay the `fitz.open()` overhead twice. No PDF caching mechanism exists.
2. **Double file reads:** Both `_png_metadata` and `ScreenshotArtifact.from_file` read the same file twice (for image metadata and SHA-256). For large PNGs at print resolution, this is avoidable I/O.
3. **Subprocess without timeout:** `compile_tex_with_tectonic` can hang indefinitely if Tectonic stalls on package downloads or compilation.
4. **Recursive glob for listing:** `list_visual_artifacts` uses `rglob`, which traverses the entire directory tree. If agents store many intermediate files in `runs/`, this scales poorly.
5. **No lazy evaluation for `plan_deck`:** `NoLLMProvider().plan_deck` is called synchronously in the MCP tool. For large excerpts, this blocks the stdio transport. While `NoLLMProvider` is deterministic and fast today, replacing it with a real LLM provider later without async infrastructure will be a breaking change.

## Improvement Tickets

### Ticket 1: Structured error enrichment for `_exception_result`
**Acceptance criteria:**
- `ValidationError` returns Pydantic `error()` JSON in `details["validation_errors"]`.
- `fitz` exceptions return the offending path in `details["path"]`.
- All existing tests pass without modification to their assertions.

**Validation:** `uv run pytest tests/test_mcp_contracts.py -v -q`

### Ticket 2: Add pre-validation for file existence and type in MCP tools
**Acceptance criteria:**
- `ingest_source` returns `missing_input` (or new `not_a_file`) if `source_path` is a directory.
- `render_source_preview`, `render_slide_preview`, `render_zoom_crop` return `missing_input` if the PDF does not exist.
- `compile_rendered_beamer` returns `missing_input` if `tex_path` does not exist.
- `create_run` returns `invalid_base_dir` if `base_dir` is an existing file.

**Validation:** `uv run pytest tests/test_mcp_contracts.py -v -q`

### Ticket 3: Eliminate double file reads in visual artifact pipeline
**Acceptance criteria:**
- `ScreenshotArtifact.from_file` reads the file exactly once.
- `_png_metadata` reads the file exactly once (either by streaming hash or by reusing Pillow's loaded data).
- SHA-256 hashes remain identical to before.

**Validation:** `uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -v -q`

### Ticket 4: Add subprocess timeout to Tectonic compilation
**Acceptance criteria:**
- `compile_tex_with_tectonic` passes `timeout=300` (or env-configurable value) to `subprocess.run`.
- Timeout raises a structured `ToolResult.error(kind="compile_timeout", ...)` instead of an unhandled exception.
- Test added mocking a slow subprocess or using a very short timeout.

**Validation:** `uv run pytest tests/test_mcp_vertical_slice.py -v -q`

### Ticket 5: Consolidate render-options parsing and add page-count validation
**Acceptance criteria:**
- Extract `_parse_render_options_safe` helper used by both preview tools.
- `render_pdf_pages` validates requested pages against `document.page_count` and returns `invalid_page_selection` for out-of-range pages.
- `render_zoom_crop` validates `page` against `document.page_count`.

**Validation:** `uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -v -q`

### Ticket 6: Document HTTP transport and add CLI arguments
**Acceptance criteria:**
- README section added explaining `server.py http` behavior, including default host/port.
- `main()` accepts `--host` and `--port` arguments when transport is `http`.
- Arcade stdio behavior remains unchanged and documented.

**Validation:** Manual test `uv run python server.py http --host 127.0.0.1 --port 8080` starts without error.

## Checklist

- [x] Source files were not modified.
- [x] Report was written to the requested path.
- [x] Commands and failures are recorded.
