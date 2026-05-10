import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.arcade_live
def test_arcade_cli_supports_local_mcp_stdio_command() -> None:
    arcade = _resolve_arcade_cli()
    if arcade is None:
        pytest.skip("Arcade CLI is not available")

    completed = subprocess.run(
        [str(arcade), "mcp", "--help"],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert completed.returncode == 0
    assert "stdio" in completed.stdout
    assert "--cwd" in completed.stdout


def _resolve_arcade_cli() -> Path | None:
    found = shutil.which("arcade") or shutil.which("arcade.exe")
    if found is not None:
        return Path(found).resolve()
    fallback = Path.home() / ".local" / "bin" / "arcade.exe"
    return fallback.resolve() if fallback.exists() else None
