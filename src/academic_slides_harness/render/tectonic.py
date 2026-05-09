from __future__ import annotations

import os
import subprocess
from pathlib import Path


def find_tectonic_executable() -> Path | None:
    candidates = [
        os.environ.get("ACADEMIC_SLIDES_TECTONIC_PATH"),
        os.environ.get("TECTONIC_PATH"),
        str(
            Path.home()
            / ".codex"
            / "plugins"
            / "cache"
            / "openai-bundled"
            / "latex-tectonic"
            / "0.1.1"
            / "bin"
            / "tectonic.exe"
        ),
        "tectonic",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return path.resolve()
    return None


def compile_tex_with_tectonic(*, tex_path: Path, output_dir: Path) -> Path:
    tectonic = find_tectonic_executable()
    if tectonic is None:
        raise FileNotFoundError("Tectonic executable was not found")

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [str(tectonic), "--outdir", str(output_dir), str(tex_path.resolve())]
    completed = subprocess.run(
        command,
        cwd=tex_path.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Tectonic failed with exit code "
            f"{completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return output_dir / tex_path.with_suffix(".pdf").name
