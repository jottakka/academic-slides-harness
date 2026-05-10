from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class BeamerSlide:
    title: str
    bullets: list[str]


@dataclass(frozen=True)
class BeamerDeck:
    title: str
    slides: list[BeamerSlide]


@dataclass(frozen=True)
class RichSlideBlock:
    type: Literal["visual", "claim", "explanation", "source_citation", "steps"]
    text: str | None = None
    artifact_path: str | None = None
    source_page: int | None = None
    items: list[str] | None = None


@dataclass(frozen=True)
class RichBeamerSlide:
    title: str
    layout: Literal["hero_visual", "figure_explanation", "workflow_steps", "takeaway"]
    blocks: list[RichSlideBlock]
    learning_goal: str | None = None


@dataclass(frozen=True)
class RichBeamerDeck:
    title: str
    slides: list[RichBeamerSlide]


def render_beamer_tex(deck: BeamerDeck) -> str:
    frames = "\n\n".join(_render_slide(slide) for slide in deck.slides)
    return "\n".join(
        [
            "\\documentclass{beamer}",
            "\\usetheme{Madrid}",
            f"\\title{{{_escape_latex(deck.title)}}}",
            "\\begin{document}",
            "\\frame{\\titlepage}",
            frames,
            "\\end{document}",
            "",
        ]
    )


def render_rich_beamer_tex(deck: RichBeamerDeck) -> str:
    frames = "\n\n".join(_render_rich_slide(slide) for slide in deck.slides)
    return "\n".join(
        [
            "\\documentclass[aspectratio=169]{beamer}",
            "\\usetheme{Boadilla}",
            "\\usepackage{graphicx}",
            "\\usepackage{xcolor}",
            "\\setbeamertemplate{navigation symbols}{}",
            "\\definecolor{ashblue}{HTML}{1F4E79}",
            "\\definecolor{ashlight}{HTML}{EAF2F8}",
            "\\setbeamercolor{frametitle}{fg=white,bg=ashblue}",
            "\\setbeamercolor{block title}{fg=white,bg=ashblue}",
            "\\setbeamercolor{block body}{bg=ashlight,fg=black}",
            f"\\title{{{_escape_latex(deck.title)}}}",
            "\\begin{document}",
            "\\begin{frame}[plain]",
            "\\vfill",
            f"\\begin{{center}}\\Huge\\color{{ashblue}} {_escape_latex(deck.title)}\\end{{center}}",
            "\\vfill",
            "\\end{frame}",
            frames,
            "\\end{document}",
            "",
        ]
    )


def _render_slide(slide: BeamerSlide) -> str:
    bullets = "\n".join(f"  \\item {_escape_latex(item)}" for item in slide.bullets)
    return "\n".join(
        [
            f"\\begin{{frame}}{{{_escape_latex(slide.title)}}}",
            "\\begin{itemize}",
            bullets,
            "\\end{itemize}",
            "\\end{frame}",
        ]
    )


def _render_rich_slide(slide: RichBeamerSlide) -> str:
    content = _render_rich_slide_body(slide)
    return "\n".join(
        [
            f"\\begin{{frame}}{{{_escape_latex(slide.title)}}}",
            content,
            "\\end{frame}",
        ]
    )


def _render_rich_slide_body(slide: RichBeamerSlide) -> str:
    visual = _first_block(slide, "visual")
    non_visual_blocks = [block for block in slide.blocks if block.type != "visual"]
    if slide.layout == "figure_explanation" and visual is not None:
        return "\n".join(
            [
                _render_learning_goal(slide),
                "\\begin{columns}[T,onlytextwidth]",
                "\\begin{column}{0.56\\textwidth}",
                _render_visual_block(visual, width="\\linewidth"),
                "\\end{column}",
                "\\begin{column}{0.40\\textwidth}",
                *[_render_rich_block(block) for block in non_visual_blocks],
                "\\end{column}",
                "\\end{columns}",
            ]
        )
    if slide.layout == "hero_visual" and visual is not None:
        return "\n".join(
            [
                _render_learning_goal(slide),
                "\\begin{center}",
                _render_visual_block(visual, width="0.82\\textwidth"),
                "\\end{center}",
                *[_render_rich_block(block) for block in non_visual_blocks],
            ]
        )
    if slide.layout == "workflow_steps":
        return "\n".join(
            [_render_learning_goal(slide), *[_render_rich_block(block) for block in slide.blocks]]
        )
    return "\n".join(
        [_render_learning_goal(slide), *[_render_rich_block(block) for block in slide.blocks]]
    )


def _render_learning_goal(slide: RichBeamerSlide) -> str:
    if not slide.learning_goal:
        return ""
    return (
        f"\\begin{{block}}{{Learning goal}}\n{_escape_latex(slide.learning_goal)}\n\\end{{block}}"
    )


def _render_rich_block(block: RichSlideBlock) -> str:
    if block.type == "visual":
        return _render_visual_block(block, width="0.76\\textwidth")
    if block.type == "claim":
        return _render_text_block("Key claim", block.text)
    if block.type == "explanation":
        return _render_text_block("Why it matters", block.text)
    if block.type == "source_citation":
        return _render_source_citation(block)
    if block.type == "steps":
        return _render_steps(block.items or [])
    return ""


def _render_visual_block(block: RichSlideBlock, *, width: str) -> str:
    if not block.artifact_path:
        return ""
    path = _latex_path(block.artifact_path)
    return f"\\includegraphics[width={width},keepaspectratio]{{\\detokenize{{{path}}}}}"


def _render_text_block(title: str, text: str | None) -> str:
    if not text:
        return ""
    return "\n".join(
        [
            f"\\begin{{block}}{{{_escape_latex(title)}}}",
            _escape_latex(text),
            "\\end{block}",
        ]
    )


def _render_source_citation(block: RichSlideBlock) -> str:
    if block.source_page is None:
        return ""
    return f"{{\\scriptsize\\color{{gray}} Source page {block.source_page}}}"


def _render_steps(items: list[str]) -> str:
    if not items:
        return ""
    rendered_items = "\n".join(f"  \\item {_escape_latex(item)}" for item in items if item.strip())
    return "\n".join(
        [
            "\\begin{enumerate}",
            rendered_items,
            "\\end{enumerate}",
        ]
    )


def _first_block(slide: RichBeamerSlide, block_type: str) -> RichSlideBlock | None:
    return next((block for block in slide.blocks if block.type == block_type), None)


def _latex_path(value: str) -> str:
    return Path(value).as_posix()


def _escape_latex(value: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)
