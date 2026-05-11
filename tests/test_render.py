from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

import fitz
import pytest

from academic_slides_harness.render.beamer import (
    BeamerDeck,
    BeamerSlide,
    RichBeamerDeck,
    RichBeamerSlide,
    RichSlideBlock,
    render_beamer_tex,
    render_rich_beamer_tex,
)
from academic_slides_harness.render.tectonic import (
    compile_tex_with_tectonic,
    find_tectonic_executable,
)


def test_render_beamer_tex_contains_real_beamer_structure() -> None:
    tex = render_beamer_tex(
        BeamerDeck(
            title="Numerical Methods",
            slides=[BeamerSlide(title="Convergence", bullets=["Residuals", "Error bounds"])],
        )
    )

    assert "\\documentclass{beamer}" in tex
    assert "\\begin{frame}{Convergence}" in tex
    assert "\\item Residuals" in tex


def test_render_beamer_tex_escapes_latex_special_characters() -> None:
    tex = render_beamer_tex(
        BeamerDeck(
            title=r"50% Growth & Cost_#1 {A} $x^2$ ~ path\file",
            slides=[
                BeamerSlide(
                    title=r"Use #, %, &, _, {braces}",
                    bullets=[r"alpha_beta costs $5 & 10% uses \escape ~ caret^"],
                )
            ],
        )
    )

    assert r"50\% Growth \& Cost\_\#1 \{A\} \$x\textasciicircum{}2\$" in tex
    assert r"\textasciitilde{} path\textbackslash{}file" in tex
    assert r"\begin{frame}{Use \#, \%, \&, \_, \{braces\}}" in tex
    assert (
        r"\item alpha\_beta costs \$5 \& 10\% uses "
        r"\textbackslash{}escape \textasciitilde{} caret\textasciicircum{}"
    ) in tex


def test_render_rich_beamer_tex_supports_visual_explanation_without_itemize(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "source preview.png"
    visual_path.write_bytes(b"not inspected by tex generation")

    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Bioimage Workflow",
            slides=[
                RichBeamerSlide(
                    title="Segment the nuclear rim",
                    layout="figure_explanation",
                    learning_goal="Connect a colorful microscopy image to a measurable boundary.",
                    blocks=[
                        RichSlideBlock(type="visual", artifact_path=str(visual_path)),
                        RichSlideBlock(
                            type="claim",
                            text=(
                                "The rim turns intensity dynamics into a reproducible measurement."
                            ),
                        ),
                        RichSlideBlock(
                            type="explanation",
                            text=(
                                "The visual contrast identifies where the workflow should measure."
                            ),
                        ),
                        RichSlideBlock(type="source_citation", source_page=21),
                    ],
                )
            ],
        )
    )

    assert "\\includegraphics" in tex
    assert "\\detokenize{" in tex
    assert "\\begin{itemize}" not in tex
    assert "Learning goal" in tex
    assert "\\ashsourcecitation{21}" in tex


def test_render_rich_beamer_tex_title_slide_has_academic_framing(tmp_path: Path) -> None:
    visual_path = tmp_path / "evidence.png"
    visual_path.write_bytes(b"not inspected by tex generation")

    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Bioimage Workflow",
            slides=[
                RichBeamerSlide(
                    title="Segment the nuclear rim",
                    layout="figure_explanation",
                    learning_goal="Connect a microscopy image to a measurable boundary.",
                    blocks=[
                        RichSlideBlock(type="visual", artifact_path=str(visual_path)),
                        RichSlideBlock(
                            type="claim",
                            text="The rim defines where intensity is measured.",
                        ),
                        RichSlideBlock(type="source_citation", source_page=21),
                    ],
                ),
                RichBeamerSlide(
                    title="Report the measurement",
                    layout="takeaway",
                    blocks=[
                        RichSlideBlock(type="claim", text="The measurement needs a citation."),
                        RichSlideBlock(type="source_citation", source_page=24),
                    ],
                ),
            ],
        )
    )

    assert "Evidence-backed academic deck" in tex
    assert "Connect a microscopy image to a measurable boundary." in tex
    assert "2 slides" in tex
    assert "1 visual evidence frame" in tex
    assert "Source pages: 21, 24" in tex
    assert "\\begin{frame}[plain]" in tex
    assert "\\setbeamertemplate{footline}{}" in tex
    assert "\\Huge\\color{ashblue}" not in tex


def test_render_rich_beamer_tex_uses_discreet_citation_footer(tmp_path: Path) -> None:
    visual_path = tmp_path / "evidence.png"
    visual_path.write_bytes(b"not inspected by tex generation")

    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Bioimage Workflow",
            slides=[
                RichBeamerSlide(
                    title="Evidence frame",
                    layout="figure_explanation",
                    blocks=[
                        RichSlideBlock(type="visual", artifact_path=str(visual_path)),
                        RichSlideBlock(type="claim", text="Evidence needs a stable reference."),
                        RichSlideBlock(type="source_citation", source_page=7),
                    ],
                )
            ],
        )
    )

    assert "\\ashsourcecitation{7}" in tex
    assert "\\scriptsize\\color{gray} Source page 7" not in tex


def test_render_rich_beamer_tex_caps_visual_height_for_figure_layout(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "evidence.png"
    visual_path.write_bytes(b"not inspected by tex generation")

    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Bioimage Workflow",
            slides=[
                RichBeamerSlide(
                    title="Evidence frame",
                    layout="figure_explanation",
                    learning_goal="Keep the image dominant without covering the claim.",
                    blocks=[
                        RichSlideBlock(type="visual", artifact_path=str(visual_path)),
                        RichSlideBlock(type="claim", text="The visual gets the largest region."),
                        RichSlideBlock(
                            type="explanation",
                            text="The explanation stays in a compact right rail.",
                        ),
                        RichSlideBlock(type="source_citation", source_page=7),
                    ],
                )
            ],
        )
    )

    assert "\\begin{column}{0.64\\textwidth}" in tex
    assert "\\begin{column}{0.32\\textwidth}" in tex
    assert "\\includegraphics[width=\\linewidth,height=0.62\\textheight,keepaspectratio]" in tex
    assert "\\ashrailclaim{" in tex


def test_render_rich_beamer_tex_uses_clean_main_claim_surface() -> None:
    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Bioimage Workflow",
            slides=[
                RichBeamerSlide(
                    title="Report the measurement boundary",
                    layout="takeaway",
                    blocks=[
                        RichSlideBlock(
                            type="claim",
                            text="A result needs an explicit measurement boundary.",
                        ),
                        RichSlideBlock(
                            type="explanation",
                            text="This prevents readers from mistaking a display choice for data.",
                        ),
                        RichSlideBlock(type="source_citation", source_page=24),
                    ],
                )
            ],
        )
    )

    assert "\\ashmainclaim{" in tex
    assert "\\ashmainexplanation{" in tex
    assert "\\begin{block}{Key claim}" not in tex
    assert "\\begin{block}{Why it matters}" not in tex


def test_render_rich_beamer_tex_renders_native_equation_and_table_blocks() -> None:
    tex = render_rich_beamer_tex(
        RichBeamerDeck(
            title="Navegacao Inercial",
            slides=[
                RichBeamerSlide(
                    title="A aceleracao especifica e vetorial",
                    layout="equation_explanation",
                    learning_goal="Interpretar a relacao entre corpo, navegacao e gravidade.",
                    blocks=[
                        RichSlideBlock(
                            type="latex_equation",
                            latex=r"f^b = R_n^b (a^n - g^n)",
                            caption="Equacao nativa para preservar semantica matematica.",
                        ),
                        RichSlideBlock(
                            type="claim",
                            text="Nao e necessario transformar formula reproduzivel em imagem.",
                        ),
                        RichSlideBlock(type="source_citation", source_page=3),
                    ],
                ),
                RichBeamerSlide(
                    title="Termos principais",
                    layout="table_explanation",
                    blocks=[
                        RichSlideBlock(
                            type="latex_table",
                            caption="Tabela nativa editavel.",
                            headers=["Termo", "Papel"],
                            rows=[["f^b", "medida"], ["g^n", "gravidade"]],
                        ),
                        RichSlideBlock(type="claim", text="Tabelas pequenas devem usar tabular."),
                        RichSlideBlock(type="source_citation", source_page=4),
                    ],
                ),
            ],
        )
    )

    assert r"f^b = R_n^b (a^n - g^n)" in tex
    assert "\\begin{tabular}" in tex
    assert "Termo" in tex
    assert "\\includegraphics" not in tex
    assert "\\usepackage{amsmath}" in tex
    assert "\\usepackage[utf8]{inputenc}" in tex


@pytest.mark.latex
def test_compile_tex_with_special_characters_when_tectonic_available(tmp_path: Path) -> None:
    tectonic = find_tectonic_executable()
    if tectonic is None:
        pytest.skip("Tectonic executable is not available")

    tex_path = tmp_path / "special.tex"
    tex_path.write_text(
        render_beamer_tex(
            BeamerDeck(
                title=r"Special 50% & Cost_#1",
                slides=[
                    BeamerSlide(
                        title=r"Escaped {A} $x^2$",
                        bullets=[r"100% reproducible & file_name.tex #1"],
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    pdf_path = compile_tex_with_tectonic(tex_path=tex_path, output_dir=tmp_path / "build")

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


@pytest.mark.latex
def test_compile_rich_beamer_with_embedded_png_when_tectonic_available(
    tmp_path: Path,
) -> None:
    tectonic = find_tectonic_executable()
    if tectonic is None:
        pytest.skip("Tectonic executable is not available")

    image_path = tmp_path / "source.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 50), False)
    pixmap.clear_with(180)
    pixmap.save(image_path)

    tex_path = tmp_path / "rich-deck.tex"
    tex_path.write_text(
        render_rich_beamer_tex(
            RichBeamerDeck(
                title="Visual Bioimage Deck",
                slides=[
                    RichBeamerSlide(
                        title="Use the source image as evidence",
                        layout="figure_explanation",
                        learning_goal="Show the image before making the claim.",
                        blocks=[
                            RichSlideBlock(type="visual", artifact_path=str(image_path)),
                            RichSlideBlock(type="claim", text="The figure is evidence."),
                            RichSlideBlock(type="source_citation", source_page=4),
                        ],
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    pdf_path = compile_tex_with_tectonic(tex_path=tex_path, output_dir=tmp_path / "build")

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_find_tectonic_executable_rejects_directory_env_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_executable_dir = tmp_path / "tectonic.exe"
    fake_executable_dir.mkdir()

    monkeypatch.setenv("ACADEMIC_SLIDES_TECTONIC_PATH", str(fake_executable_dir))
    monkeypatch.delenv("TECTONIC_PATH", raising=False)

    assert find_tectonic_executable() is None


def test_find_tectonic_executable_does_not_probe_user_tool_cache_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundled = (
        tmp_path
        / ".tool-cache"
        / "plugins"
        / "cache"
        / "bundled-tools"
        / "latex-tectonic"
        / "0.1.1"
        / "bin"
        / "tectonic.exe"
    )
    bundled.parent.mkdir(parents=True)
    bundled.write_text("fake tectonic", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("ACADEMIC_SLIDES_TECTONIC_PATH", raising=False)
    monkeypatch.delenv("TECTONIC_PATH", raising=False)
    monkeypatch.setattr("academic_slides_harness.render.tectonic.shutil.which", lambda _name: None)

    assert find_tectonic_executable() is None


def test_compile_tex_with_tectonic_times_out_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tectonic = tmp_path / "tectonic.exe"
    tectonic.write_text("fake", encoding="utf-8")
    tex_path = tmp_path / "deck.tex"
    tex_path.write_text("\\documentclass{beamer}", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> CompletedProcess[str]:
        raise TimeoutExpired(cmd=kwargs.get("args", args[0] if args else []), timeout=1)

    monkeypatch.setenv("ACADEMIC_SLIDES_TECTONIC_PATH", str(tectonic))
    monkeypatch.setattr("academic_slides_harness.render.tectonic.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="timed out"):
        compile_tex_with_tectonic(
            tex_path=tex_path,
            output_dir=tmp_path / "build",
            timeout_seconds=1,
        )


@pytest.mark.latex
def test_compile_tex_with_bundled_tectonic_when_available(tmp_path: Path) -> None:
    tectonic = find_tectonic_executable()
    if tectonic is None:
        pytest.skip("Tectonic executable is not available")

    tex_path = tmp_path / "deck.tex"
    tex_path.write_text(
        render_beamer_tex(
            BeamerDeck(title="Tiny Deck", slides=[BeamerSlide(title="One", bullets=["A"])])
        ),
        encoding="utf-8",
    )

    pdf_path = compile_tex_with_tectonic(tex_path=tex_path, output_dir=tmp_path / "build")

    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
