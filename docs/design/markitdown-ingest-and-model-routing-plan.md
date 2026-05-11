# MarkItDown Ingestion And Model Routing Plan

Checked on 2026-05-11 against the current repository tree, MarkItDown 0.1.5,
the local Ollama server, and the MCP 2025-11-25 sampling schema.

## Goal

Add a source-ingestion path that can produce cleaner Markdown from PDFs and
common office/data files while preserving the project's deterministic baseline.
Model-assisted extraction should be explicit, optional, and marked as
non-deterministic.

## Current Repo Baseline

- `src/academic_slides_harness/ingest/pdf.py` uses `pdfplumber` for PDF page
  count and page text.
- `src/academic_slides_harness/visualize/preview.py` uses PyMuPDF for rendered
  page previews and crops.
- `src/academic_slides_harness/llm/providers.py` already has a small
  `OllamaProvider` for optional live checks and a deterministic `NoLLMProvider`.
- `academic-slides-harness doctor secrets` already scans repo docs/config for
  raw key patterns without printing secret values.
- There is no MCP tool yet that lists available LLM/OCR providers or redacted
  model configuration.

## Verified MarkItDown Findings

Local command:

```powershell
uv run --with "markitdown[pdf]" python -c "from markitdown import MarkItDown; md=MarkItDown(enable_plugins=False); print(hasattr(md, 'convert_local')); print([m for m in dir(md) if m.startswith('convert')])"
```

Findings:

- MarkItDown 0.1.5 is available through `uvx` / `uv run --with`.
- Python API exposes `convert_local`, `convert_stream`, `convert_response`,
  `convert_uri`, `convert_url`, and `convert`.
- For this project, prefer `convert_local` or `convert_stream`; avoid generic
  `convert` for untrusted input because it can handle local and remote sources.
- The result object exposes `text_content`, `markdown`, and `title`.
- The image-processing fixture converted to about 35k Markdown characters.
- The output preserved spaces better than the current `pdfplumber` extraction on
  the fixture opening paragraph, but it needs `unicodedata.normalize("NFKC", ...)`
  to normalize ligatures such as `fi` and `fl`.
- MarkItDown is designed for LLM/text-analysis Markdown, not high-fidelity
  visual reconstruction.

Important MarkItDown features to use:

- Optional extras can be installed per file family: `pdf`, `docx`, `pptx`,
  `xlsx`, `xls`, `outlook`, `az-doc-intel`, `audio-transcription`, and
  `youtube-transcription`.
- Plugins are disabled by default and can be enabled only for explicit
  non-deterministic modes.
- `llm_client`, `llm_model`, and `llm_prompt` can be passed to MarkItDown for
  model-assisted image descriptions.
- The `markitdown-ocr` plugin can use an OpenAI-compatible client to OCR images
  embedded in PDF, DOCX, PPTX, and XLSX files.
- Azure Document Intelligence is supported but should remain out of the default
  local path because it is a cloud dependency.

## Verified Local Model Findings

Local command:

```powershell
uv run python -c "from academic_slides_harness.llm.providers import OllamaProvider; p=OllamaProvider(); print(p.is_available()); print(p.list_models())"
```

Findings:

- `ollama` executable is present.
- The Ollama server is available at the existing default
  `http://127.0.0.1:11434`.
- Local models reported during this check:
  - `gemma4:latest`
  - `nomic-embed-text:latest`
  - `qwen2.5-coder:7b`
  - `qwen3.5:9b`
  - `qwen3.6:latest`
- `OPENAI_API_KEY` was not set in the current shell.
- `AZURE_OPENAI_API_KEY` was not set in the current shell.
- `OPENAI_BASE_URL` was not set in the current shell.

No tool should print secret values. Provider checks should return booleans,
configured variable names, model names, endpoints when they are not secret, and
warnings.

## MCP Sampling Finding

The MCP schema defines `sampling/createMessage` as a server-to-client request
where the client chooses the model and should keep user approval in the loop.
Client capability negotiation controls whether sampling is available.

The installed `arcade_mcp_server.Context` exposes:

```python
await context.sampling.create_message(
    messages,
    system_prompt=...,
    include_context=...,
    temperature=...,
    max_tokens=...,
    model_preferences=...,
)
```

Its implementation checks `ClientCapabilities(sampling={})` before calling the
client session. Therefore sampling can be used only as an optional enrichment
path. It should not be required for CI, stdio smoke, deterministic extraction,
or normal deck rendering.

Recommended sampling use:

- good fit: ask the calling client model to produce a grounded teaching outline
  from already-extracted Markdown and source-page metadata;
- good fit: ask for candidate slide claims or a short figure relevance review;
- bad fit: raw OCR or source-of-truth extraction, because sampling output is
  client-dependent and human-approval dependent;
- bad fit: default MarkItDown conversion, because conversion should work without
  client model support.

## Architecture Decision

Use three explicit modes:

```text
deterministic_markdown
  MarkItDown offline, plugins disabled, no model calls.

local_llm_ocr
  MarkItDown plus markitdown-ocr and an OpenAI-compatible local or configured
  client. Non-deterministic, optional, and always marked as model-assisted.

client_sampling_enrichment
  MCP sampling through the calling client model. Non-deterministic, optional,
  and separate from source conversion.
```

Do not remove PyMuPDF visual tools. They remain the source of truth for rendered
previews, crops, dimensions, hashes, and visual quality metadata.

Do not fully replace `ExtractSourcePages` in the first pass. MarkItDown produces
cleaner whole-document text for planning, but the existing page extractor still
provides page-bounded excerpts for citations and page checks. Replacement should
happen only after side-by-side quality tests on the real fixture.

## Proposed MCP Tools

### `ListModelProviders`

Purpose: let agents choose deterministic or model-assisted paths without seeing
secrets.

Structured content:

```json
{
  "ollama": {
    "available": true,
    "base_url": "http://127.0.0.1:11434",
    "models": ["..."],
    "vision_model_candidates": ["..."],
    "embedding_model_candidates": ["..."]
  },
  "openai": {
    "api_key_configured": false,
    "base_url_configured": false,
    "configured_env_vars": []
  },
  "azure_openai": {
    "api_key_configured": false,
    "endpoint_configured": false,
    "configured_env_vars": []
  },
  "markitdown": {
    "available": true,
    "version": "0.1.5",
    "ocr_plugin_available": false
  }
}
```

Rules:

- never print raw API keys, bearer tokens, private keys, or credential file
  contents;
- report only `*_configured` booleans and variable names;
- include a warning when Ollama is available but no likely vision model is
  installed;
- keep parameters JSON-friendly.

### `ExtractSourceMarkdown`

Purpose: convert supported source files to normalized Markdown.

Parameters:

- `source_path: str`
- `output_dir: str`
- `mode: str = "deterministic_markdown"`
- `pages: str = ""` for future PDF page slicing; empty means whole source
- `overwrite: bool = false`
- `ollama_base_url: str = "http://127.0.0.1:11434"` for model-assisted mode
- `model: str = ""` for model-assisted mode

Structured content:

```json
{
  "source_path": "...",
  "source_sha256": "...",
  "source_kind": "pdf",
  "mode": "deterministic_markdown",
  "deterministic": true,
  "markdown_path": "...",
  "markdown_sha256": "...",
  "char_count": 35756,
  "page_break_count": 16,
  "heading_candidates": [],
  "figure_reference_count": 64,
  "warnings": []
}
```

Rules:

- deterministic mode must use `MarkItDown(enable_plugins=False)` and
  `convert_local`;
- normalize output with `NFKC` and compact unsafe surrogate characters;
- write Markdown to caller-provided `output_dir`;
- return typed errors for missing input, unsupported mode, missing dependency,
  artifact exists, conversion failure, and missing model/provider;
- never place generated Markdown in tracked paths unless a test fixture
  explicitly requires it.

### `SampleMarkdownTeachingPlan` or later equivalent

Purpose: optional client-sampling enrichment from extracted Markdown.

Status: spike after `ExtractSourceMarkdown`, not first implementation.

Rules:

- tool must accept an optional `Context` from `arcade_mcp_server`;
- if no session or sampling capability is available, return typed
  `sampling_unavailable`;
- include `deterministic: false`;
- request JSON-like compact output and validate it before returning;
- never use sampling output as a citation source unless it points back to source
  pages or artifact IDs.

## Chunk Plan

### Chunk 1: Provider Discovery And Redaction

Scope:

- add provider discovery helpers under `src/academic_slides_harness/llm`;
- add `ListModelProviders` MCP tool;
- optionally add `academic-slides-harness doctor models --json` backed by the
  same helper.

Acceptance:

- Ollama availability and model list are returned when the server is reachable;
- OpenAI/Azure config is reported as booleans without secret leakage;
- missing Ollama degrades to `available: false`;
- in-process MCP registry includes `list_model_providers`;
- stdio MCP smoke can call the tool.

Risk:

- local Ollama availability is machine-dependent.

Rollback:

- remove the new helper, tool registration, and tests; no data migration.

Validation:

- `uv run pytest tests/test_llm.py tests/test_mcp_contracts.py tests/test_cli.py -q`
- `uv run pytest -m "not ollama and not arcade_live" -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`
- `uv run pytest -m ollama -q` only when specifically validating live local
  Ollama behavior.

### Chunk 2: Deterministic MarkItDown Markdown Extraction

Scope:

- add MarkItDown dependency with minimal extras, likely
  `markitdown[pdf,docx,pptx,xlsx]>=0.1.5`;
- add `src/academic_slides_harness/ingest/markdown.py`;
- add `ExtractSourceMarkdown` MCP tool in deterministic mode only.

Acceptance:

- fixture PDF produces a Markdown artifact with source hash, markdown hash,
  char count, page-break count, and figure-reference count;
- `NFKC` normalization removes ligature artifacts in extracted text;
- missing/corrupt input returns typed errors;
- existing `ExtractSourcePages` remains unchanged.

Risk:

- MarkItDown dependency graph may add heavier transitive packages than current
  PDF-only ingest.

Rollback:

- remove dependency, new ingest module, tool registration, and tests; keep
  existing `pdfplumber` path.

Validation:

- failing-first test against the real fixture;
- `uv run pytest tests/test_ingest_markdown.py tests/test_mcp_contracts.py -q`
- full non-live gate plus Arcade stdio gate.

### Chunk 3: Planning Uses Markdown When Available

Scope:

- update agent-facing resources/prompts to prefer `ExtractSourceMarkdown` for
  planning text;
- add an optional `markdown_excerpts` input to planner helpers only if needed;
- keep `ExtractSourcePages` for page-cited excerpts.

Acceptance:

- a deck plan can be generated from MarkItDown Markdown without word-join
  regressions seen in the current `pdfplumber` fixture text;
- page citations still come from source pages/crops, not ungrounded Markdown;
- old `PlanDeck` inputs continue to work.

Risk:

- whole-document Markdown can lose exact page locality after conversion.

Rollback:

- prompt/resource-only rollback; keep the extraction tool available.

Validation:

- `uv run pytest tests/test_llm.py tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
- real fixture extraction comparison report in `runs/`, not tracked.

### Chunk 4: Local LLM OCR Mode

Scope:

- add optional `markitdown-ocr` dependency only if the dependency footprint is
  acceptable;
- wire `local_llm_ocr` mode through an OpenAI-compatible client;
- support Ollama-compatible base URL and configured OpenAI-compatible endpoints.

Acceptance:

- mode is rejected with typed `model_provider_unavailable` if no model/provider
  is configured;
- output clearly states `deterministic: false`;
- model name, provider, temperature, prompt hash, and conversion warnings are
  recorded;
- deterministic mode stays the default and does not import or require OCR
  plugin behavior.

Risk:

- local vision support varies by model; output can hallucinate OCR text.

Rollback:

- remove OCR mode while preserving deterministic MarkItDown extraction.

Validation:

- deterministic unit tests with faked OpenAI-compatible client for routing and
  redaction;
- optional live Ollama smoke only when a vision-capable model is installed;
- no long raw LLM prose snapshots.

### Chunk 5: Sampling Feasibility Spike

Scope:

- add one narrow experimental tool or internal adapter that calls
  `context.sampling.create_message`;
- return `sampling_unavailable` when client capability is absent;
- use sampling only for teaching-plan enrichment, not conversion or citations.

Acceptance:

- in-process tests cover capability unavailable and fake sampling success;
- stdio live smoke verifies the tool registers and returns a recoverable result
  with the current client;
- docs state that sampling depends on client support and approval.

Risk:

- some clients will not expose sampling; Arcade stdio test clients may not
  provide a sampling callback.

Rollback:

- remove the experimental sampling tool without affecting extraction.

Validation:

- `uv run pytest tests/test_mcp_contracts.py tests/test_mcp_stdio.py -q`
- `uv run academic-slides-harness doctor arcade --json`
- `uv run pytest -m arcade_live -q`

### Chunk 6: Side-By-Side Extractor Evaluation

Scope:

- compare `pdfplumber` page extraction and MarkItDown whole-document Markdown
  on the checked-in open-access PDF fixture;
- produce a run report with text length, ligature count, word-join heuristics,
  figure reference count, and planning usefulness notes.

Acceptance:

- report shows whether MarkItDown should become the preferred planning text
  source;
- no generated report is committed unless it is a compact fixture/test expected
  output;
- criteria are objective enough to use as regression checks.

Risk:

- one fixture is not enough to decide for all academic PDFs.

Rollback:

- keep both extractors and delay default selection.

Validation:

- `uv run pytest tests/test_ingest_markdown.py tests/test_open_access_book_e2e.py -q`

### Chunk 7: Default Route Decision

Scope:

- decide whether `PlanDeck` and prompt resources should prefer
  `ExtractSourceMarkdown` by default;
- keep `ExtractSourcePages` available for page-local citation and fallback.

Acceptance:

- docs and MCP prompts state the intended tool order;
- real deck generation still compiles and previews;
- final deck validator still requires source page/crop evidence.

Risk:

- agents may over-trust cleaned Markdown and skip visual evidence.

Rollback:

- revert prompt/tool-order docs to the old page-excerpt flow.

Validation:

- full normal gate;
- Arcade stdio gate;
- one real MCP deck run against the image-processing fixture.

## Out Of Scope For First Implementation

- Cloud Azure Document Intelligence as a required path.
- Remote URL conversion through MarkItDown.
- Automatic trust in LLM OCR text.
- Replacing PyMuPDF previews/crops.
- Removing `ExtractSourcePages`.
- Using sampling as a required path.

## Recommended First Ticket

Start with Chunk 1. It is the lowest-risk foundation because it gives agents a
truthful, redacted view of local model availability before any tool chooses a
deterministic or model-assisted extraction path.

Then implement Chunk 2. MarkItDown should first land as an offline deterministic
source-to-Markdown tool with fixture evidence before any LLM/OCR behavior is
introduced.
