# Planning, Execution, and Review Rules

Use this workflow for non-trivial changes in the harness.

1. Restate the goal and identify the affected subsystem.
2. Write or update tests before production code.
3. Run the targeted failing test and confirm the failure is meaningful.
4. Implement the smallest production change that satisfies the test.
5. Run targeted tests, then the full non-live gate.
6. Review changed files for unrelated churn, missing structured outputs, and weak tests.
7. Report commands run, failures fixed, skipped live checks, and residual risk.

Tests are weak when they only assert that a function was called, only cover a mock, or do not prove a behavior the project relies on.

## Visual Deck Ticket Flow

Use smaller roles when the change affects slide quality:

- Explorer: identify existing renderer, MCP contracts, fixtures, prompts, and quality gaps.
- Implementer: own a narrow file set and start with a failing behavior test.
- Visual reviewer: inspect rendered PNGs/crops and judge layout, density, hierarchy, and evidence.
- MCP verifier: confirm stdio MCP tool discovery and at least one real tool call for MCP-facing changes.

Required gates for render/MCP changes:

- Targeted failing test before production code.
- Targeted pass after implementation.
- Real compile/render evidence when Tectonic is available.
- `uv run pytest -m "not ollama and not arcade_live" -q`.
- `uv run academic-slides-harness doctor arcade --json`.
- `uv run pytest -m arcade_live -q`.
