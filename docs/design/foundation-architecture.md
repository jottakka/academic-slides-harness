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

`validate_run` must validate required run paths and parse `manifest.json` against
`RunManifest`; existence-only manifest checks are not enough evidence that a run
is usable.

## Visual/Didactic Deck Quality Direction

The original `title + bullets` Beamer contract is a v0 compatibility path. It is
useful for deterministic smoke tests, but insufficient for high-quality academic
teaching decks because it forces agents into generic bullet summaries.

The v1 visual deck direction is a rich slide contract:

- named layouts such as `hero_visual`, `figure_explanation`, `workflow_steps`,
  and `takeaway`;
- typed blocks such as `visual`, `claim`, `explanation`, `steps`, and
  `source_citation`;
- real visual artifacts copied into the render output and embedded with
  `\includegraphics`;
- source-page or artifact evidence for claims;
- rendered PNG previews and zoom crops as acceptance evidence.

Agents may choose text, layout, and evidence, but production rendering stays
deterministic and avoids raw LaTeX injection by default.
