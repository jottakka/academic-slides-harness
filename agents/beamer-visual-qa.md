# Beamer and Visual QA Rules

Use visual evidence for deck quality.

- Compile `.tex` with Tectonic when available.
- Render PDF pages/slides to PNG previews before claiming visual quality.
- Use `fast` previews for iteration, `review` previews for normal acceptance, and `print` for high-resolution inspection.
- Generate zoom crops for dense formulas, citations, small text, diagrams, and layout problem areas.
- Store preview artifacts outside tracked source files, normally under `runs/<run>/screenshots` or a test `tmp_path`.
- Report screenshot paths, dimensions, DPI, scale, zoom, and hashes.

Do not judge slide quality from source text alone when a render path is available.
