# Kimi Core and Render Review - 2026-05-10

## Scope

### Source files inspected
- src/academic_slides_harness/core/models.py
- src/academic_slides_harness/core/state_machines.py
- src/academic_slides_harness/ingest/pdf.py
- src/academic_slides_harness/llm/providers.py
- src/academic_slides_harness/render/beamer.py
- src/academic_slides_harness/render/tectonic.py
- src/academic_slides_harness/cli.py
- src/academic_slides_harness/mcp/server.py
- src/academic_slides_harness/visualize/preview.py
- src/academic_slides_harness/visualize/options.py

### Test files inspected
- tests/test_models.py
- tests/test_state_machines.py
- tests/test_ingest_pdf.py
- tests/test_llm.py
- tests/test_render.py
- tests/test_cli.py
- tests/test_ollama_live.py
- tests/test_visualize.py
- tests/test_mcp_contracts.py
- tests/test_mcp_vertical_slice.py

### Other documents inspected
- README.md
- docs/bug-reports/arcade-mcp/2026-05-09-arcade-cli-and-local-engine-unavailable.md
- docs/bug-reports/arcade-mcp/2026-05-09-local-arcade-config-secret-exposure.md

### Commands run
- `uv run pytest -m "not ollama and not arcade_live" -q` -> 50 passed, 2 deselected in 12.59s
- `uv run ruff format --check .` -> 30 files already formatted
- `uv run ruff check .` -> All checks passed
- `uv run python -c` probes for edge cases in `_escape_latex`, `NoLLMProvider`, `find_tectonic_executable`, `CropBox`, `main([])`, `parse_page_selection`, `_validate_manifest_file`, `_slug`, `_body_to_bullets`, `render_pdf_pages` with out-of-range pages, and `compile_tex_with_tectonic` with bad input.

---

## Findings

### P0 - `find_tectonic_executable` may return a directory instead of a file
- **Severity:** P0
- **Area:** `src/academic_slides_harness/render/tectonic.py`, `find_tectonic_executable()`, lines 25-31
- **Evidence:**
  ```python
  for candidate in candidates:
      if not candidate:
          continue
      path = Path(candidate)
      if path.exists():
          return path.resolve()
  ```
  Reproduction: create a directory named `tectonic.exe`, set `ACADEMIC_SLIDES_TECTONIC_PATH` to it, and the function returns the directory path.
  ```
  directory returned: C:\...\tectonic.exe
  is file: False
  ```
- **Impact:** `subprocess.run` later tries to execute a directory, producing a cryptic OS error instead of a clear "Tectonic not found" message.
- **Recommendation:** Change `path.exists()` to `path.is_file()`.
- **Confidence:** high

### P1 - `ScreenshotArtifact.from_file` reads the entire file twice
- **Severity:** P1
- **Area:** `src/academic_slides_harness/core/models.py`, `from_file()`, lines 74-87
- **Evidence:**
  ```python
  resolved = path.resolve()
  return cls(
      artifact_id=f"{target}-p{page}-{sha256_bytes(resolved.read_bytes())[:12]}",
      ...
      sha256=sha256_bytes(resolved.read_bytes()),
      ...
  )
  ```
  `resolved.read_bytes()` is called on line 76 and again on line 85.
- **Impact:** For large PNG artifacts (print-resolution crops), I/O and memory usage double with every artifact creation.
- **Recommendation:** Read once into a local variable and reuse it for both the artifact_id suffix and the sha256 field.
- **Confidence:** high

### P1 - `compile_tex_with_tectonic` calls `subprocess.run` without a timeout
- **Severity:** P1
- **Area:** `src/academic_slides_harness/render/tectonic.py`, `compile_tex_with_tectonic()`, lines 41-47
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
  No `timeout` argument is provided.
- **Impact:** If Tectonic hangs during package fetching or compilation, the pipeline thread hangs indefinitely. In an MCP server context this can block the tool indefinitely.
- **Recommendation:** Add `timeout=300` (or a caller-provided timeout) and translate `subprocess.TimeoutExpired` into a clear `ToolResult` or `RuntimeError` message.
- **Confidence:** high

### P1 - CLI `doctor` with no sub-target silently prints version and exits 0
- **Severity:** P1
- **Area:** `src/academic_slides_harness/cli.py`, `main()`, lines 16-24
- **Evidence:**
  ```python
  if args.command == "doctor" and args.doctor_target == "arcade":
      return _doctor_arcade(args)
  if args.command == "doctor" and args.doctor_target == "secrets":
      return _doctor_secrets(args)
  print(f"academic-slides-harness {__version__}")
  return 0
  ```
  Running `main(["doctor"])` falls through to the print/return-0 path because `args.doctor_target` is `None`.
  Command output:
  ```
  exit: 0
  output: academic-slides-harness 0.1.0
  ```
- **Impact:** A user typing `academic-slides-harness doctor` without a sub-target believes the doctor check succeeded when no checks ran.
- **Recommendation:** Add an explicit `elif args.command == "doctor"` branch that prints the doctor help text and returns a non-zero exit code.
- **Confidence:** high

### P1 - `_check_local_stdio_entrypoint` resolves `server.py` against `Path.cwd()` instead of the project root
- **Severity:** P1
- **Area:** `src/academic_slides_harness/cli.py`, `_check_local_stdio_entrypoint()`, line 217
- **Evidence:**
  ```python
  server_path = project_root / "server.py"
  ```
  where `project_root = Path.cwd()` from the caller in `diagnose_arcade`.
- **Impact:** Running the doctor from a subdirectory of the repo (e.g., `src/`) falsely reports that `server.py` is missing, even though it exists at the repository root.
- **Recommendation:** Resolve the project root from `__file__` (e.g., `Path(__file__).resolve().parents[2]`) instead of `Path.cwd()`, or add a `--project-root` CLI flag.
- **Confidence:** high

### P1 - `OllamaProvider.list_models` and `embed` lack exception handling
- **Severity:** P1
- **Area:** `src/academic_slides_harness/llm/providers.py`, `list_models()` lines 50-54 and `embed()` lines 56-67
- **Evidence:**
  ```python
  def list_models(self) -> list[str]:
      response = httpx.get(...)
      response.raise_for_status()
      payload = response.json()
      ...
  ```
  Neither method catches `httpx.HTTPError` or `json.JSONDecodeError`. `is_available()` does catch `httpx.HTTPError`, but the other methods do not.
- **Impact:** If Ollama is running but returns a non-2xx status or malformed JSON, the caller crashes instead of gracefully degrading to the deterministic `NoLLMProvider` fallback. The AGENTS.md policy says: "If Ollama is unavailable or disabled, use deterministic fallback providers and report that fallback explicitly."
- **Recommendation:** Wrap network and parsing calls in try/except and raise a well-typed exception (or return an empty list / None) that the caller can map to a fallback.
- **Confidence:** high

### P2 - `inspect_pdf` reads the PDF file twice
- **Severity:** P2
- **Area:** `src/academic_slides_harness/ingest/pdf.py`, `inspect_pdf()`, lines 10-18
- **Evidence:**
  ```python
  with pdfplumber.open(resolved) as pdf:
      pages = len(pdf.pages)
  return SourceDocument(
      ...
      sha256=sha256_bytes(resolved.read_bytes()),
  )
  ```
  `pdfplumber.open()` reads the file, then `resolved.read_bytes()` reads it again for hashing.
- **Impact:** Linear scaling penalty for large PDFs (e.g., textbooks). A 100 MB PDF incurs ~200 MB of disk reads.
- **Recommendation:** Hash from a single streamed read, or if `pdfplumber` exposes the underlying bytes, reuse them. Alternatively, read the file into a `bytes` variable once and pass a `BytesIO` to `pdfplumber.open` while also hashing the same bytes.
- **Confidence:** high

### P2 - `render_pdf_pages` and `render_zoom_crop` silently overwrite existing files
- **Severity:** P2
- **Area:** `src/academic_slides_harness/visualize/preview.py`, lines 32-33 and 70-71
- **Evidence:**
  ```python
  output_path = output_dir / f"{target}-p{page_number}-{resolved.dpi}dpi.png"
  pixmap.save(output_path)
  ```
  No existence check before saving.
- **Impact:** Re-running a preview tool with the same output directory and parameters destroys prior artifacts and sidecars without warning.
- **Recommendation:** Add an optional `exist_ok: bool = True` parameter, or raise when the target path already exists unless explicitly allowed.
- **Confidence:** high

### P2 - `NoLLMProvider.plan_deck` can produce a `DeckPlan` with zero slides
- **Severity:** P2
- **Area:** `src/academic_slides_harness/llm/providers.py`, `plan_deck()`, lines 22-33
- **Evidence:**
  ```python
  clean_excerpts = [normalize_whitespace(excerpt) for excerpt in excerpts if excerpt.strip()]
  selected = clean_excerpts[: max(1, max_slides)]
  slides = tuple(... for index, excerpt in enumerate(selected, start=1))
  ```
  If `excerpts` is empty or all whitespace-only, `clean_excerpts` is empty, `selected` is empty, and `slides` is an empty tuple.
  Reproduction output:
  ```
  empty excerpt: 0
  whitespace excerpt: 0
  empty list: 0
  ```
- **Impact:** A downstream renderer may produce a deck with only a title page, which is probably not the caller's intent. The `DeckPlan` model allows an empty tuple.
- **Recommendation:** Either document that empty excerpts yield an empty deck, or enforce at least one slide (e.g., a placeholder slide with the title and a "no excerpts" body).
- **Confidence:** medium

### P2 - `CropBox` dataclass accepts negative width and height
- **Severity:** P2
- **Area:** `src/academic_slides_harness/visualize/options.py`, `CropBox`, lines 14-20
- **Evidence:**
  ```python
  @dataclass(frozen=True)
  class CropBox:
      x: float
      y: float
      width: float
      height: float
      normalized: bool = True
  ```
  Reproduction: `CropBox(x=0, y=0, width=-1, height=1)` is accepted without error.
- **Impact:** Negative dimensions propagate to `_resolve_crop` and `get_pixmap(clip=...)`, causing a `fitz` error later. The MCP layer (`_parse_crop_box`) guards this, but direct consumers of `CropBox` are unprotected.
- **Recommendation:** Add `__post_init__` validation to require `width > 0` and `height > 0`.
- **Confidence:** high

### P2 - `list_visual_artifacts` succeeds with an empty list when the directory does not exist
- **Severity:** P2
- **Area:** `src/academic_slides_harness/mcp/server.py`, `list_visual_artifacts()`, lines 291-306
- **Evidence:**
  ```python
  png_paths = sorted(directory.rglob("*.png")) if directory.exists() else []
  artifacts = [_png_metadata(path) for path in png_paths]
  return ToolResult.success(...)
  ```
- **Impact:** A caller passing a typo in the screenshots path gets a success response with 0 artifacts, making the typo hard to detect.
- **Recommendation:** Return a `ToolResult.error(kind="missing_input", ...)` when the directory does not exist.
- **Confidence:** high

### P3 - Test `test_no_llm_provider_creates_deterministic_deck_plan` overclaims determinism
- **Severity:** P3
- **Area:** `tests/test_llm.py`, lines 4-19
- **Evidence:** The test exercises the provider once and checks output shape. It does not invoke it a second time to assert identical output, nor does it test boundary inputs (empty excerpts, whitespace, `max_slides=0`).
- **Impact:** Test name implies determinism is verified, but the test only validates structure.
- **Recommendation:** Rename to `test_no_llm_provider_creates_expected_deck_plan` or add a second call with identical inputs and assert equality.
- **Confidence:** medium

### P3 - `_body_to_bullets` strips bullet markers but not numbered list markers
- **Severity:** P3
- **Area:** `src/academic_slides_harness/mcp/server.py`, `_body_to_bullets()`, lines 408-425
- **Evidence:**
  ```python
  lines = [re.sub(r"^[-*]\s*", "", line).strip() for line in body.splitlines() if line.strip()]
  ```
  Only `^[-*]\s*` is stripped. A body like `1. First\n2. Second` will preserve the `1.` and `2.` prefixes.
- **Impact:** Numbered list markers leak into Beamer itemize bullets, producing visually inconsistent slides.
- **Recommendation:** Extend the regex to also strip `^\d+\.\s*` prefixes, or document that only bullet-style lists are supported.
- **Confidence:** medium

---

## Performance Notes

1. **Redundant file reads in artifact hashing**
   - `inspect_pdf` reads the PDF twice (pdfplumber + `read_bytes()`).
   - `ScreenshotArtifact.from_file` reads the PNG twice (artifact_id + sha256).
   - `list_visual_artifacts` reads every PNG fully for SHA-256 even when the caller only wants a listing.
   - **Cheap win:** Cache or stream bytes once per file.

2. **Secret scan resolves every file path eagerly**
   - `_iter_secret_scan_files` calls `candidate.resolve()` inside the loop. For large trees this adds syscalls.
   - **Cheap win:** Resolve only files that are not filtered out.

3. **No timeout on Tectonic compilation**
   - As noted in findings, a hanging `tectonic` process blocks the thread forever.
   - **Cheap win:** Add a `timeout` parameter to `subprocess.run`.

4. **`render_pdf_pages` processes pages sequentially**
   - For a 50-page source PDF preview, pages are rendered one at a time. `fitz` is single-threaded, but batching could help if this moves to a process pool later.
   - **Note:** Not a current bottleneck; worth tracking if preview batch sizes grow.

5. **`_iter_secret_scan_files` walks ignored directories before filtering**
   - `path.rglob("*")` descends into `.git`, `.venv`, etc., and then filters. For large `.venv` directories this wastes time.
   - **Cheap win:** Use `os.walk` with explicit pruning of ignored directory names.

---

## Improvement Tickets

### Ticket 1: Harden Tectonic discovery and compilation
- **Acceptance criteria:**
  1. `find_tectonic_executable` rejects directories and non-executable files.
  2. `compile_tex_with_tectonic` accepts a `timeout_seconds` parameter (default 300) and raises a clear `RuntimeError` on timeout.
  3. Tests cover both behaviors without requiring a real Tectonic installation (use `tmp_path` and mock candidates).
- **Suggested validation:** `uv run pytest -m "not ollama and not arcade_live" -q`

### Ticket 2: Add out-of-bounds page validation to PDF preview tools
- **Acceptance criteria:**
  1. `render_pdf_pages` validates that every requested page is `<= document.page_count` before rendering.
  2. `render_zoom_crop` validates that the requested page is in bounds before cropping.
  3. Both raise a clear `ValueError` (or return a typed MCP error) instead of a raw `fitz` exception.
  4. Tests verify the new behavior with a 1-page PDF and a request for page 5.
- **Suggested validation:** `uv run pytest tests/test_visualize.py tests/test_mcp_contracts.py -q`

### Ticket 3: Reduce redundant file I/O in ingestion and artifact creation
- **Acceptance criteria:**
  1. `inspect_pdf` computes the SHA-256 from a single read (or streams from the same bytes used by pdfplumber).
  2. `ScreenshotArtifact.from_file` reads the file exactly once.
  3. `list_visual_artifacts` does not compute SHA-256 when the caller only needs paths and dimensions (or make hashing optional).
  4. No test coverage is lost.
- **Suggested validation:** `uv run pytest tests/test_models.py tests/test_ingest_pdf.py tests/test_mcp_contracts.py -q`

### Ticket 4: Fix CLI `doctor` subcommand handling and project-root resolution
- **Acceptance criteria:**
  1. `academic-slides-harness doctor` (no target) prints help and exits non-zero.
  2. `_check_local_stdio_entrypoint` resolves `server.py` relative to the installed package root, not `Path.cwd()`.
  3. Tests verify both behaviors.
- **Suggested validation:** `uv run pytest tests/test_cli.py -q`

### Ticket 5: Harden `OllamaProvider` error handling and fallback signaling
- **Acceptance criteria:**
  1. `list_models` catches `httpx.HTTPError` and `json.JSONDecodeError`, returning an empty list instead of crashing.
  2. `embed` catches the same exceptions and raises a well-typed `RuntimeError` with a message that callers can map to fallback behavior.
  3. Add a unit test that mocks an `httpx` timeout and asserts graceful degradation.
- **Suggested validation:** `uv run pytest tests/test_llm.py tests/test_ollama_live.py -q`

### Ticket 6: Expand LaTeX render tests for special characters and edge cases
- **Acceptance criteria:**
  1. A test asserts that `_escape_latex` correctly handles every character in the replacement map.
  2. A test asserts that `render_beamer_tex` produces valid-looking LaTeX when slide titles contain `&`, `%`, `$`, `_`, `{`, `}`, `~`, `^`, and backslash.
  3. A test asserts that an empty `bullets` list still produces compilable LaTeX (even if visually empty).
- **Suggested validation:** `uv run pytest tests/test_render.py -q`

---

## Checklist

- [x] Source files were not modified.
- [x] Report was written to the requested path: `docs/reviews/external/2026-05-10-kimi-core-render-review.md`
- [x] Commands and failures are recorded in the Scope and Evidence sections.
