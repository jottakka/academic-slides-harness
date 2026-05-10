from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from academic_slides_harness.core.models import sha256_file


@dataclass(frozen=True)
class RichLayoutPattern:
    name: str
    purpose: str
    when_to_use: str
    required_blocks: tuple[str, ...]
    suggested_text_limits: dict[str, int]
    example: dict[str, Any]


LAYOUT_PATTERNS: dict[str, RichLayoutPattern] = {
    "hero_visual": RichLayoutPattern(
        name="hero_visual",
        purpose="Make one visual artifact carry the main teaching claim.",
        when_to_use="Use for a striking figure, image, diagram, or crop that can anchor a slide.",
        required_blocks=("visual", "claim", "source_citation"),
        suggested_text_limits={"title": 72, "learning_goal": 120, "claim": 140, "explanation": 180},
        example={
            "title": "Nuclei are segmented before intensity is measured",
            "layout": "hero_visual",
            "learning_goal": "Connect segmentation masks to downstream measurement.",
            "blocks": [
                {"type": "visual", "artifact_path": "C:/abs/path/source_pdf-p21-144dpi.png"},
                {
                    "type": "claim",
                    "text": "The segmentation mask defines where the measurement is valid.",
                },
                {"type": "source_citation", "source_page": 21},
            ],
        },
    ),
    "figure_explanation": RichLayoutPattern(
        name="figure_explanation",
        purpose="Pair visual evidence with a concise explanation.",
        when_to_use="Use when a figure needs one explicit claim and one short interpretive note.",
        required_blocks=("visual", "claim", "explanation", "source_citation"),
        suggested_text_limits={"title": 72, "learning_goal": 110, "claim": 120, "explanation": 220},
        example={
            "title": "Boundary crops reveal the measurement target",
            "layout": "figure_explanation",
            "learning_goal": "Explain why the boundary is the region of interest.",
            "blocks": [
                {"type": "visual", "artifact_path": "C:/abs/path/source_pdf-p21-crop-144dpi.png"},
                {"type": "claim", "text": "The relevant signal is localized at the rim."},
                {
                    "type": "explanation",
                    "text": (
                        "A tight crop keeps attention on the measurement boundary "
                        "instead of the full field."
                    ),
                },
                {"type": "source_citation", "source_page": 21},
            ],
        },
    ),
    "workflow_steps": RichLayoutPattern(
        name="workflow_steps",
        purpose="Show a process as ordered stages instead of paragraph notes.",
        when_to_use="Use for methods, pipelines, algorithms, or before-after processing chains.",
        required_blocks=("steps", "source_citation"),
        suggested_text_limits={"title": 68, "learning_goal": 110, "step": 55, "max_steps": 5},
        example={
            "title": "The image analysis workflow has four gates",
            "layout": "workflow_steps",
            "learning_goal": (
                "Track the order of preprocessing, segmentation, measurement, and review."
            ),
            "blocks": [
                {
                    "type": "steps",
                    "items": [
                        "Normalize input channels",
                        "Segment the target structure",
                        "Measure intensity in the region",
                        "Review artifacts before reporting",
                    ],
                },
                {"type": "source_citation", "source_page": 18},
            ],
        },
    ),
    "takeaway": RichLayoutPattern(
        name="takeaway",
        purpose="Compress a section into one memorable conclusion.",
        when_to_use="Use after several evidence slides or at the end of a short deck.",
        required_blocks=("claim", "source_citation"),
        suggested_text_limits={"title": 64, "learning_goal": 90, "claim": 180, "explanation": 180},
        example={
            "title": "Takeaway",
            "layout": "takeaway",
            "learning_goal": "State the durable idea from the visual evidence.",
            "blocks": [
                {
                    "type": "claim",
                    "text": (
                        "A good slide makes the evidence visible before it asks "
                        "the audience to accept the claim."
                    ),
                },
                {"type": "source_citation", "source_page": 21},
            ],
        },
    ),
}


def parse_layout_selection(selection: str) -> list[str]:
    raw_selection = selection.strip()
    if not raw_selection or raw_selection.lower() == "all":
        return list(LAYOUT_PATTERNS)
    layouts = [item.strip() for item in raw_selection.split(",") if item.strip()]
    unknown = [layout for layout in layouts if layout not in LAYOUT_PATTERNS]
    if unknown:
        known = ", ".join(LAYOUT_PATTERNS)
        raise ValueError(f"Unsupported layout(s): {', '.join(unknown)}. Known layouts: {known}")
    return layouts


def render_layout_placeholder_images(
    *,
    output_dir: Path,
    layouts: list[str],
    width: int = 1280,
    height: int = 720,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    if width < 640 or height < 360:
        raise ValueError("Placeholder dimensions must be at least 640x360.")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for layout in layouts:
        pattern = LAYOUT_PATTERNS[layout]
        output_path = output_dir / f"layout-{layout.replace('_', '-')}-placeholder.png"
        if output_path.exists() and not overwrite:
            raise FileExistsError(output_path)
        _draw_placeholder(output_path=output_path, pattern=pattern, width=width, height=height)
        artifacts.append(
            {
                "layout": layout,
                "path": str(output_path.resolve()),
                "width": width,
                "height": height,
                "format": "png",
                "sha256": sha256_file(output_path),
                "purpose": pattern.purpose,
                "required_blocks": list(pattern.required_blocks),
                "suggested_text_limits": pattern.suggested_text_limits,
            }
        )
    return artifacts


def layout_catalog_markdown() -> str:
    sections = [
        "# Rich Slide Layout Patterns",
        "",
        "Use these patterns before calling `RenderRichBeamer`. Pick the layout that serves the "
        "learning objective; do not default to bullet-summary slides.",
        "",
    ]
    for pattern in LAYOUT_PATTERNS.values():
        sections.extend(
            [
                f"## {pattern.name}",
                "",
                f"Purpose: {pattern.purpose}",
                f"When to use: {pattern.when_to_use}",
                f"Required blocks: {', '.join(pattern.required_blocks)}",
                f"Suggested text limits: {pattern.suggested_text_limits}",
                "Example JSON:",
                "```json",
                _compact_json(pattern.example),
                "```",
                "",
            ]
        )
    sections.extend(
        [
            "To see visual placeholders, call `RenderLayoutPlaceholders` with an output directory.",
            "Generated placeholder PNGs are run artifacts and should not be committed.",
        ]
    )
    return "\n".join(sections)


def rich_slide_schema_markdown() -> str:
    return "\n".join(
        [
            "# Rich Slide Plan Schema",
            "",
            "A rich deck call to `RenderRichBeamer` uses a title and a list of slide objects.",
            "",
            "Supported layouts: hero_visual, figure_explanation, workflow_steps, takeaway.",
            "Supported block types: visual, claim, explanation, steps, source_citation.",
            "",
            "Rules:",
            "- `hero_visual` and `figure_explanation` require one `visual` block.",
            "- `visual.artifact_path` must point to an existing PNG, JPG, or JPEG artifact.",
            "- Claims should cite either a source page or a visual artifact used on the slide.",
            "- Keep text short enough for the selected layout limits.",
            "- Text over the layout limits returns typed `text_overflow_risk` before "
            "assets are copied.",
            "- Use `RenderLayoutPlaceholders` before generation when an agent needs "
            "layout guidance.",
        ]
    )


def _draw_placeholder(
    *,
    output_path: Path,
    pattern: RichLayoutPattern,
    width: int,
    height: int,
) -> None:
    image = Image.new("RGB", (width, height), "#f7f4ec")
    draw = ImageDraw.Draw(image)
    title_font = _font(26)
    label_font = _font(20)
    small_font = _font(16)
    margin = 52
    header_h = 92
    accent = "#1f4e79"
    pale = "#dbe9f5"
    ink = "#1f2933"
    draw.rectangle((0, 0, width, header_h), fill=accent)
    _draw_text(
        draw,
        (margin, 26),
        pattern.name.replace("_", " ").title(),
        fill="white",
        font=title_font,
    )
    _draw_text(
        draw,
        (width - 430, 34),
        "Learning goal / source page",
        fill="white",
        font=small_font,
    )
    body_top = header_h + 34
    body_bottom = height - margin
    if pattern.name == "hero_visual":
        _box(
            draw,
            (115, body_top, width - 115, body_bottom - 96),
            "VISUAL EVIDENCE",
            pale,
            ink,
            label_font,
            small_font,
        )
        _box(
            draw,
            (180, body_bottom - 72, width - 180, body_bottom),
            "KEY CLAIM",
            "white",
            ink,
            label_font,
            small_font,
        )
    elif pattern.name == "figure_explanation":
        _box(
            draw,
            (margin, body_top, int(width * 0.58), body_bottom),
            "VISUAL / CROP",
            pale,
            ink,
            label_font,
            small_font,
        )
        x0 = int(width * 0.62)
        _box(
            draw,
            (x0, body_top, width - margin, body_top + 145),
            "KEY CLAIM",
            "white",
            ink,
            label_font,
            small_font,
        )
        _box(
            draw,
            (x0, body_top + 175, width - margin, body_bottom - 70),
            "WHY IT MATTERS",
            "white",
            ink,
            label_font,
            small_font,
        )
        _box(
            draw,
            (x0, body_bottom - 45, width - margin, body_bottom),
            "SOURCE",
            "#eeeeee",
            ink,
            label_font,
            small_font,
        )
    elif pattern.name == "workflow_steps":
        step_w = (width - (margin * 2) - 48) // 4
        for index in range(4):
            x0 = margin + index * (step_w + 16)
            _box(
                draw,
                (x0, body_top + 120, x0 + step_w, body_top + 345),
                f"STEP {index + 1}",
                pale if index % 2 == 0 else "white",
                ink,
                label_font,
                small_font,
            )
    else:
        _box(
            draw,
            (160, body_top + 70, width - 160, body_top + 260),
            "TAKEAWAY CLAIM",
            "white",
            ink,
            label_font,
            small_font,
        )
        _box(
            draw,
            (260, body_top + 310, width - 260, body_top + 390),
            "SOURCE / EVIDENCE",
            pale,
            ink,
            label_font,
            small_font,
        )
    _draw_wrapped(
        draw,
        (margin, height - 34),
        pattern.purpose,
        fill=ink,
        font=small_font,
        width_chars=140,
    )
    image.save(output_path)


def _box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    label: str,
    fill: str,
    outline: str,
    label_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=outline, width=3)
    x0, y0, x1, y1 = xy
    _draw_text(draw, (x0 + 20, y0 + 20), label, fill=outline, font=label_font)
    _draw_text(draw, (x1 - 175, y1 - 38), "placeholder", fill="#667085", font=small_font)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: str,
    font: ImageFont.ImageFont,
    width_chars: int,
) -> None:
    x, y = xy
    for offset, line in enumerate(wrap(text, width=width_chars)):
        _draw_text(draw, (x, y + offset * 14), line, fill=fill, font=font)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: str,
    font: ImageFont.ImageFont,
) -> None:
    draw.text(xy, text, fill=fill, font=font)


def _compact_json(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, indent=2)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()
