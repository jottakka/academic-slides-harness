# Summary

<!-- What changed and why? Keep this concrete. -->

## Type Of Change

- [ ] Documentation only
- [ ] Test only
- [ ] Bug fix
- [ ] Feature
- [ ] MCP/tool contract change
- [ ] Visual/rendering change
- [ ] Configuration/workflow change

## Status Claims

- Implemented:
  -
- Experimental:
  -
- Planned / not implemented:
  -

## Validation

Required for most changes:

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest -m "not ollama and not arcade_live" -q`

Required when MCP, Arcade, render contracts, visual tools, or MCP docs changed:

- [ ] `uv run academic-slides-harness doctor arcade --json`
- [ ] `uv run pytest -m arcade_live -q`

Recommended for public docs/config changes:

- [ ] `uv run academic-slides-harness doctor secrets --json`
- [ ] Public docs/configs checked for private paths and credentials

## Visual Or Artifact Evidence

<!-- Required for visual/rendering changes. Link paths under runs/ only as local evidence; do not commit generated artifacts. -->

- Source previews:
- Deck previews:
- Zoom crops:
- Compiled PDF:

## Generated Artifacts

- [ ] No generated artifacts were committed
- [ ] Only intentional fixtures were committed

## Risks And Limitations

<!-- What remains uncertain, skipped, or intentionally out of scope? -->

