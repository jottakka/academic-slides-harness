"""Small CLI entrypoint for smoke checks."""

from academic_slides_harness import __version__


def main() -> None:
    print(f"academic-slides-harness {__version__}")
