# Beamer and Visual QA Rules

Use visual evidence for deck quality.

- Compile `.tex` with Tectonic when available.
- Render PDF pages/slides to PNG previews before claiming visual quality.
- Use `fast` previews for iteration, `review` previews for normal acceptance, and `print` for high-resolution inspection.
- Generate zoom crops for dense formulas, citations, small text, diagrams, and layout problem areas.
- Store preview artifacts outside tracked source files, normally under `runs/<run>/screenshots` or a test `tmp_path`.
- Report screenshot paths, dimensions, DPI, scale, zoom, and hashes.

Do not judge slide quality from source text alone when a render path is available.

## Visual Rubric

- Prefer rich layouts over default bullet frames for visual source material.
- Use source previews or crops as evidence when the source has meaningful figures.
- Check hierarchy: title, figure, claim, explanation, and citation must be visually distinct.
- Check density: reject slides that are mostly text or unreadable at review resolution.
- Check consistency: repeated layout choices should look intentional, not accidental.

## Didactic Rubric

- Each slide should have a learning goal or clear teaching purpose.
- Claims must be tied to source pages, source excerpts, or visual artifacts.
- A deck should progress from context to mechanism to implication.
- Avoid generic bullet summaries when a diagram, comparison, or figure explanation would teach better.
- A compiled deck that looks like a list of disconnected bullets is not acceptable.

## Failure Conditions

- No rendered PNG preview for a changed visual deck.
- No zoom crop for dense or visually important content.
- Claims without source evidence.
- Visual source material available, but no slide uses a visual artifact.
- Rich slide requests implemented by raw LaTeX injection instead of a safe schema.
