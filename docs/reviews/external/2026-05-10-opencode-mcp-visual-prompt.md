OpenCode: manage this task using UWL

You are an external read-only reviewer for the Academic Slides Harness repo.

Repo:
- cwd: C:\Users\fjlim\Documents\Codex\academic-slides-harness
- Language/runtime: Python 3.13, uv, Arcade MCP, Pydantic, PyMuPDF/pdfplumber, Jinja2, Tectonic.

Rules:
- Do not edit source code, tests, config, or docs except for writing your final report to the exact report path below.
- Preserve unrelated changes. Do not revert anything.
- Treat `arcade_live` as local stdio MCP runtime, not engine/worker HTTP endpoints by default.
- Prefer concrete evidence over broad opinions.
- If you run commands, keep them read-only and record exact commands/results. Do not run the full test suite if another agent may be using uv.

Report path:
- docs/reviews/external/2026-05-10-opencode-mcp-visual-review.md

Review block A: MCP and Arcade contracts
- server.py
- src/academic_slides_harness/mcp/server.py
- tests/test_mcp_contracts.py
- tests/test_mcp_stdio.py
- tests/test_arcade_live.py
- README.md Arcade sections
- docs/design/foundation-architecture.md MCP notes

Review block B: visual artifacts and render-facing MCP behavior
- src/academic_slides_harness/visualize/options.py
- src/academic_slides_harness/visualize/preview.py
- tests/test_visualize.py
- tests/test_mcp_vertical_slice.py
- agents/arcade-mcp-qa.md
- agents/beamer-visual-qa.md

Primary questions:
1. Bugs: Find concrete defects, edge cases, contract mismatches, path handling problems, structured output gaps, or Windows stdio issues.
2. Performance: Identify avoidable repeated PDF/image reads, expensive metadata paths, subprocess risks, or scaling issues for larger academic PDFs.
3. Code quality: Look for unclear boundaries, overly broad functions, weak typing, missing validation, or poor error consistency.
4. Improvements: Propose small, high-value next tickets. Favor changes that improve agent-facing MCP reliability.

Finding format:
- Severity: P0/P1/P2/P3.
- Area: file path and line/function when possible.
- Evidence: quote or summarize the relevant code/test behavior, plus any command output you ran.
- Impact: why it matters for this repo.
- Recommendation: concrete fix or test to add.
- Confidence: high/medium/low.

Final report structure:
# OpenCode MCP and Visual Review - 2026-05-10

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
