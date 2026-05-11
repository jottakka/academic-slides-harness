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
            "\\usepackage{ragged2e}",
            "\\setbeamertemplate{navigation symbols}{}",
            "\\setbeamertemplate{footline}{}",
            "\\definecolor{ashblue}{HTML}{1F4E79}",
            "\\definecolor{ashnavy}{HTML}{12344F}",
            "\\definecolor{ashaccent}{HTML}{C87F2A}",
            "\\definecolor{ashlight}{HTML}{EAF2F8}",
            "\\definecolor{ashsurface}{HTML}{F7FAFC}",
            "\\definecolor{ashmuted}{HTML}{52606D}",
            "\\definecolor{ashtext}{HTML}{111827}",
            "\\setbeamercolor{normal text}{fg=ashtext,bg=white}",
            "\\setbeamercolor{frametitle}{fg=ashnavy,bg=white}",
            "\\setbeamerfont{frametitle}{series=\\bfseries,size=\\large}",
            "\\setbeamercolor{block title}{fg=white,bg=ashblue}",
            "\\setbeamercolor{block body}{bg=ashlight,fg=ashtext}",
            "\\setbeamercolor{ashTitleBand}{fg=white,bg=ashblue}",
            "\\setbeamercolor{ashFocusBox}{fg=ashtext,bg=ashlight}",
            "\\setbeamercolor{ashStatBox}{fg=ashtext,bg=ashsurface}",
            "\\setbeamercolor{ashClaimBox}{fg=ashtext,bg=ashlight}",
            "\\setbeamercolor{ashExplainBox}{fg=ashtext,bg=ashsurface}",
            "\\setbeamercolor{ashMainClaimBox}{fg=ashtext,bg=ashlight}",
            "\\setbeamercolor{ashMainExplainBox}{fg=ashtext,bg=ashsurface}",
            "\\setbeamercolor{ashLearningBox}{fg=ashtext,bg=ashsurface}",
            (
                "\\newcommand{\\ashsourcecitation}[1]{\\vspace{0.08cm}"
                "{\\raggedleft\\scriptsize\\color{ashmuted} Source page~#1\\par}}"
            ),
            (
                "\\newcommand{\\ashlearninggoal}[1]{"
                "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.12cm]"
                "{ashLearningBox}{\\scriptsize\\bfseries\\color{ashblue} Learning goal}"
                "\\quad{\\scriptsize #1}\\end{beamercolorbox}\\vspace{0.14cm}}"
            ),
            (
                "\\newcommand{\\ashrailclaim}[1]{"
                "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.18cm]"
                "{ashClaimBox}{\\scriptsize\\bfseries\\color{ashblue} Key claim}\\par"
                "\\vspace{0.06cm}{\\small #1}\\end{beamercolorbox}}"
            ),
            (
                "\\newcommand{\\ashrailexplanation}[1]{\\vspace{0.12cm}"
                "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.16cm]"
                "{ashExplainBox}{\\scriptsize\\bfseries\\color{ashmuted} Why it matters}\\par"
                "\\vspace{0.04cm}{\\scriptsize #1}\\end{beamercolorbox}}"
            ),
            (
                "\\newcommand{\\ashmainclaim}[1]{"
                "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.22cm]"
                "{ashMainClaimBox}{\\footnotesize\\bfseries\\color{ashblue} Key claim}\\par"
                "\\vspace{0.06cm}{\\large #1}\\end{beamercolorbox}}"
            ),
            (
                "\\newcommand{\\ashmainexplanation}[1]{\\vspace{0.16cm}"
                "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.18cm]"
                "{ashMainExplainBox}{\\footnotesize\\bfseries\\color{ashmuted} Why it matters}\\par"
                "\\vspace{0.04cm}{\\normalsize #1}\\end{beamercolorbox}}"
            ),
            f"\\title{{{_escape_latex(deck.title)}}}",
            "\\begin{document}",
            _render_rich_title_frame(deck),
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
            f"\\begin{{frame}}[t]{{{_escape_latex(slide.title)}}}",
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
                "\\begin{column}{0.64\\textwidth}",
                _render_visual_block(visual, width="\\linewidth", height="0.62\\textheight"),
                "\\end{column}",
                "\\begin{column}{0.32\\textwidth}",
                *[_render_rich_block(block, rail=True) for block in non_visual_blocks],
                "\\end{column}",
                "\\end{columns}",
            ]
        )
    if slide.layout == "hero_visual" and visual is not None:
        return "\n".join(
            [
                _render_learning_goal(slide),
                "\\begin{center}",
                _render_visual_block(visual, width="0.88\\textwidth", height="0.54\\textheight"),
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
    return f"\\ashlearninggoal{{{_escape_latex(slide.learning_goal)}}}"


def _render_rich_block(block: RichSlideBlock, *, rail: bool = False) -> str:
    if block.type == "visual":
        return _render_visual_block(block, width="0.76\\textwidth", height="0.54\\textheight")
    if block.type == "claim":
        return _render_claim(block.text, rail=rail)
    if block.type == "explanation":
        return _render_explanation(block.text, rail=rail)
    if block.type == "source_citation":
        return _render_source_citation(block)
    if block.type == "steps":
        return _render_steps(block.items or [])
    return ""


def _render_visual_block(block: RichSlideBlock, *, width: str, height: str | None = None) -> str:
    if not block.artifact_path:
        return ""
    path = _latex_path(block.artifact_path)
    options = [f"width={width}"]
    if height is not None:
        options.append(f"height={height}")
    options.append("keepaspectratio")
    return f"\\includegraphics[{','.join(options)}]{{\\detokenize{{{path}}}}}"


def _render_claim(text: str | None, *, rail: bool) -> str:
    if not text:
        return ""
    escaped = _escape_latex(text)
    if rail:
        return f"\\ashrailclaim{{{escaped}}}"
    return f"\\ashmainclaim{{{escaped}}}"


def _render_explanation(text: str | None, *, rail: bool) -> str:
    if not text:
        return ""
    escaped = _escape_latex(text)
    if rail:
        return f"\\ashrailexplanation{{{escaped}}}"
    return f"\\ashmainexplanation{{{escaped}}}"


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
    return f"\\ashsourcecitation{{{block.source_page}}}"


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


def _render_rich_title_frame(deck: RichBeamerDeck) -> str:
    slide_count = len(deck.slides)
    visual_count = sum(1 for slide in deck.slides if _first_block(slide, "visual") is not None)
    focus = _deck_focus(deck)
    source_pages = _deck_source_pages(deck)
    source_text = (
        "Source pages: " + ", ".join(str(page) for page in source_pages)
        if source_pages
        else "Source pages: not specified"
    )
    slide_count_text = _count_label(slide_count, "slide", "slides")
    visual_count_text = _count_label(
        visual_count,
        "visual evidence frame",
        "visual evidence frames",
    )
    return "\n".join(
        [
            "\\begin{frame}[plain]",
            "\\begin{beamercolorbox}[wd=\\paperwidth,sep=0.42cm,leftskip=0.42cm]{ashTitleBand}",
            f"{{\\Large\\bfseries {_escape_latex(deck.title)}}}\\\\[0.10cm]",
            "{\\small Evidence-backed academic deck}",
            "\\end{beamercolorbox}",
            "\\vspace{0.42cm}",
            "\\begin{columns}[T,onlytextwidth]",
            "\\begin{column}{0.62\\textwidth}",
            "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.24cm]{ashFocusBox}",
            "{\\scriptsize\\bfseries\\color{ashblue} FOCUS}\\\\[0.06cm]",
            f"{{\\large {_escape_latex(focus)}}}",
            "\\end{beamercolorbox}",
            "\\end{column}",
            "\\begin{column}{0.32\\textwidth}",
            "\\begin{beamercolorbox}[rounded=true,wd=\\linewidth,sep=0.20cm]{ashStatBox}",
            "{\\scriptsize\\bfseries\\color{ashblue} STRUCTURE}\\\\[0.08cm]",
            f"{{\\small {slide_count_text}}}\\\\",
            f"{{\\small {visual_count_text}}}",
            "\\end{beamercolorbox}",
            "\\end{column}",
            "\\end{columns}",
            "\\vfill",
            f"{{\\scriptsize\\color{{ashmuted}} {_escape_latex(source_text)}}}",
            "\\end{frame}",
        ]
    )


def _deck_focus(deck: RichBeamerDeck) -> str:
    for slide in deck.slides:
        if slide.learning_goal:
            return slide.learning_goal
    for slide in deck.slides:
        claim = _first_block(slide, "claim")
        if claim is not None and claim.text:
            return claim.text
    if deck.slides:
        return deck.slides[0].title
    return "Evidence-backed academic synthesis"


def _deck_source_pages(deck: RichBeamerDeck) -> list[int]:
    pages = {
        block.source_page
        for slide in deck.slides
        for block in slide.blocks
        if block.type == "source_citation" and block.source_page is not None
    }
    return sorted(pages)


def _count_label(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


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
