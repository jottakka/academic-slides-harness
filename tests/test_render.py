from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

import pytest

from academic_slides_harness.render.beamer import BeamerDeck, BeamerSlide, render_beamer_tex
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


def test_find_tectonic_executable_rejects_directory_env_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_executable_dir = tmp_path / "tectonic.exe"
    fake_executable_dir.mkdir()

    monkeypatch.setenv("ACADEMIC_SLIDES_TECTONIC_PATH", str(fake_executable_dir))
    monkeypatch.delenv("TECTONIC_PATH", raising=False)

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
