from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BeamerSlide:
    title: str
    bullets: list[str]


@dataclass(frozen=True)
class BeamerDeck:
    title: str
    slides: list[BeamerSlide]


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
