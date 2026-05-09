from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, arbitrary_types_allowed=True)


class SourceDocument(StrictModel):
    path: Path
    kind: Literal["pdf", "book"]
    pages: int = Field(strict=True, ge=1)
    sha256: str | None = None


class PageArtifact(StrictModel):
    path: Path
    page: int = Field(strict=True, ge=1)
    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    sha256: str


class SlideDraft(StrictModel):
    title: str
    body: str
    source_excerpt: str | None = None


class DeckPlan(StrictModel):
    title: str
    slides: tuple[SlideDraft, ...]


class ValidationReport(StrictModel):
    ok: bool
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class ScreenshotArtifact(StrictModel):
    artifact_id: str
    path: Path
    target: Literal["source_pdf", "deck_pdf"]
    page: int = Field(strict=True, ge=1)
    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    dpi: int = Field(strict=True, gt=0)
    scale: float = Field(strict=True, gt=0)
    zoom: float = Field(strict=True, gt=0)
    sha256: str
    created_at: datetime

    @classmethod
    def from_file(
        cls,
        *,
        path: Path,
        target: Literal["source_pdf", "deck_pdf"],
        page: int,
        width: int,
        height: int,
        dpi: int,
        scale: float,
        zoom: float,
    ) -> ScreenshotArtifact:
        resolved = path.resolve()
        return cls(
            artifact_id=f"{target}-p{page}-{sha256_bytes(resolved.read_bytes())[:12]}",
            path=resolved,
            target=target,
            page=page,
            width=width,
            height=height,
            dpi=dpi,
            scale=scale,
            zoom=zoom,
            sha256=sha256_bytes(resolved.read_bytes()),
            created_at=datetime.now(UTC),
        )

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": str(self.path),
            "target": self.target,
            "page": self.page,
            "width": self.width,
            "height": self.height,
            "resolution": {"dpi": self.dpi, "scale": self.scale},
            "zoom": self.zoom,
            "sha256": self.sha256,
            "created_at": self.created_at.isoformat(),
        }


class RunManifest(StrictModel):
    run_id: str
    run_dir: Path
    title: str
    state: str
    created_at: datetime
    sources: tuple[SourceDocument, ...] = ()
    screenshots: tuple[ScreenshotArtifact, ...] = ()

    @classmethod
    def create(cls, *, run_dir: Path, title: str) -> RunManifest:
        return cls(
            run_id=uuid4().hex,
            run_dir=run_dir.resolve(),
            title=title,
            state="created",
            created_at=datetime.now(UTC),
        )

    def to_structured_content(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "title": self.title,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "sources": [source.model_dump(mode="json") for source in self.sources],
            "screenshots": [artifact.to_structured_content() for artifact in self.screenshots],
        }


class ToolResult(StrictModel):
    ok: bool
    content_text: str
    structured_content: dict[str, Any]

    @property
    def is_error(self) -> bool:
        return not self.ok

    @classmethod
    def success(cls, *, message: str, structured_content: dict[str, Any]) -> ToolResult:
        return cls(ok=True, content_text=message, structured_content=structured_content)

    @classmethod
    def error(cls, *, kind: str, message: str, details: dict[str, Any] | None = None) -> ToolResult:
        return cls(
            ok=False,
            content_text=f"{kind}: {message}",
            structured_content={
                "error": {"kind": kind, "message": message, "details": details or {}}
            },
        )


def sha256_bytes(content: bytes) -> str:
    return sha256(content).hexdigest()
