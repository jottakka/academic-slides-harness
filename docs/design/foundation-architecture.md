# Foundation Architecture

Academic Slides Harness is a deterministic, LaTeX-first pipeline with optional local LLM support.

## Boundaries

- `core`: Pydantic models, state machines, hashes, and validation contracts.
- `ingest`: source inspection and text/layout extraction.
- `render`: Beamer source generation and Tectonic compilation.
- `visualize`: PNG previews, zoom crops, resolution presets, and screenshot metadata.
- `llm`: optional providers with deterministic fallback.
- `mcp`: Arcade MCP tool registration and agent-facing contracts.

## State Machines

Pipeline state is explicit:

`created -> ingesting -> ingested -> planning -> planned -> rendering -> rendered -> visualizing -> visualized -> validating -> validated|failed`

Tool calls are explicit:

`idle -> received -> eliciting|running -> progress -> completed|tool_error|fatal_error`

Invalid transitions should fail loudly in tests and runtime orchestration.

## Initial MCP Contract

Tools must expose JSON-friendly parameters, structured outputs, and typed errors. Visual tools are first-class and must return paths to generated PNGs so another agent can inspect the artifacts.
