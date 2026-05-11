You are an external read-only reviewer for the Academic Slides Harness repo.

ASCII-only output.

Repo:
- cwd: <repo-root>
- Language/runtime: Python 3.13, uv, Arcade MCP, Pydantic, PyMuPDF/pdfplumber, Jinja2, Tectonic.

Rules:
- Do not edit source code, tests, config, or docs except for writing your final report to the exact report path below.
- Preserve unrelated changes. Do not revert anything.
- Local LLMs are optional accelerators and must not be correctness dependencies.
- Prefer concrete file/line evidence over broad opinions.
- If you run commands, keep them read-only and record exact commands/results. Do not run the full test suite if another agent may be using uv.

Report path:
- docs/reviews/external/2026-05-10-kimi-core-render-review.md

Review block A: core models and deterministic state
- src/academic_slides_harness/core/models.py
- src/academic_slides_harness/core/state_machines.py
- tests/test_models.py
- tests/test_state_machines.py

Review block B: ingestion, planning, render, and CLI diagnostics
- src/academic_slides_harness/ingest/pdf.py
- src/academic_slides_harness/llm/providers.py
- src/academic_slides_harness/render/beamer.py
- src/academic_slides_harness/render/tectonic.py
- src/academic_slides_harness/cli.py
- tests/test_ingest_pdf.py
- tests/test_llm.py
- tests/test_render.py
- tests/test_cli.py
- tests/test_ollama_live.py
- README.md setup and validation sections
- docs/bug-reports/arcade-mcp/*.md

Primary questions:
1. Bugs: Find concrete data-model, PDF ingest, fallback planning, LaTeX escaping, subprocess, CLI diagnostic, or test coverage issues.
2. Performance: Identify avoidable full-file reads, repeated subprocess calls, slow scans, memory risks, or large-PDF scaling issues.
3. Code quality: Look for weak types, inconsistent errors, unclear ownership, hidden assumptions, or test names that overclaim.
4. Improvements: Propose small, high-value next tickets. Favor deterministic behavior and low-mock integration coverage.

Finding format:
- Severity: P0/P1/P2/P3.
- Area: file path and line/function when possible.
- Evidence: quote or summarize the relevant code/test behavior, plus any command output you ran.
- Impact: why it matters for this repo.
- Recommendation: concrete fix or test to add.
- Confidence: high/medium/low.

Final report structure:
# Kimi Core and Render Review - 2026-05-10

## Scope
List files inspected and commands run.

## Findings
List actionable findings in severity order. If none, say "No actionable findings."

## Performance Notes
List performance risks and cheap wins.

## Improvement Tickets
List 3-6 next tickets with acceptance criteria and suggested validation commands.

## Checklist
- Source files were not modified.
- Report was written to the requested path.
- Commands and failures are recorded.
