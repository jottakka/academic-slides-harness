from __future__ import annotations

import sys


def _force_utf8_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_force_utf8_stdio()

from academic_slides_harness.mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
