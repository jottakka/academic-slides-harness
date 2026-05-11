from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_tectonic_executable() -> Path | None:
    for env_name in ("ACADEMIC_SLIDES_TECTONIC_PATH", "TECTONIC_PATH"):
        configured = os.environ.get(env_name)
        if configured:
            path = Path(configured)
            return path.resolve() if path.is_file() else None

    candidates = ["tectonic"]
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path.resolve()
        executable = shutil.which(candidate)
        if executable:
            resolved = Path(executable).resolve()
            if resolved.is_file():
                return resolved
    return None


def compile_tex_with_tectonic(
    *,
    tex_path: Path,
    output_dir: Path,
    timeout_seconds: float = 300,
) -> Path:
    tectonic = find_tectonic_executable()
    if tectonic is None:
        raise FileNotFoundError("Tectonic executable was not found")
    if not tex_path.is_file():
        raise FileNotFoundError(f"TeX file not found: {tex_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [str(tectonic), "--outdir", str(output_dir), str(tex_path.resolve())]
    try:
        completed = subprocess.run(
            command,
            cwd=tex_path.parent,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Tectonic timed out after {timeout_seconds:g} seconds for {tex_path}"
        ) from exc
    if completed.returncode != 0:
        raise RuntimeError(
            "Tectonic failed with exit code "
            f"{completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return output_dir / tex_path.with_suffix(".pdf").name
