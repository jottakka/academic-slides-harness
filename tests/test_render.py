from pathlib import Path

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
