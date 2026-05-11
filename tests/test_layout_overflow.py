from pathlib import Path

from PIL import Image, ImageDraw

from academic_slides_harness.visualize.overflow import (
    LayoutOverflowRegion,
    assess_layout_overflow,
    parse_tex_box_warnings,
)


def test_layout_overflow_detects_ink_in_protected_region(tmp_path: Path) -> None:
    image_path = tmp_path / "deck_pdf-p1-144dpi.png"
    image = Image.new("RGB", (1000, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((660, 240, 820, 270), fill="black")
    image.save(image_path)

    report = assess_layout_overflow(
        image_path,
        regions=[
            LayoutOverflowRegion(
                label="right rail guard",
                x=0.64,
                y=0.18,
                width=0.10,
                height=0.60,
                max_ink_ratio=0.01,
            )
        ],
    )

    content = report.to_structured_content()
    assert content["ok"] is False
    assert content["warnings"][0]["kind"] == "protected_region_ink"
    assert content["warnings"][0]["details"]["label"] == "right rail guard"


def test_layout_overflow_allows_clean_protected_region(tmp_path: Path) -> None:
    image_path = tmp_path / "deck_pdf-p1-144dpi.png"
    image = Image.new("RGB", (1000, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 120, 420, 300), fill="black")
    image.save(image_path)

    report = assess_layout_overflow(
        image_path,
        regions=[
            LayoutOverflowRegion(
                label="right rail guard",
                x=0.64,
                y=0.18,
                width=0.10,
                height=0.60,
                max_ink_ratio=0.01,
            )
        ],
    )

    assert report.to_structured_content()["ok"] is True
    assert report.to_structured_content()["warnings"] == []


def test_parse_tex_box_warnings_extracts_overfull_lines() -> None:
    warnings = parse_tex_box_warnings(
        """
        warning: deck.tex:182: Underfull \\hbox (badness 10000) in paragraph
        warning: deck.tex:277: Overfull \\hbox (18.2pt too wide) in paragraph
        """
    )

    assert warnings["overfull_count"] == 1
    assert warnings["underfull_count"] == 1
    assert warnings["overfull_lines"][0]["line"] == 277
    assert warnings["overfull_lines"][0]["excess_pt"] == 18.2
