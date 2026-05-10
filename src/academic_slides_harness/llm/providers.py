from __future__ import annotations

import re
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Protocol

import httpx

from academic_slides_harness.core.models import DeckPlan, SlideDraft


class DeckPlanner(Protocol):
    def plan_deck(self, *, title: str, excerpts: list[str], max_slides: int) -> DeckPlan: ...


@dataclass(frozen=True)
class NoLLMProvider:
    """Deterministic deck planner used when local or remote LLMs are unavailable."""

    words_per_slide: int = 34

    def plan_deck(self, *, title: str, excerpts: list[str], max_slides: int) -> DeckPlan:
        clean_excerpts = [normalize_whitespace(excerpt) for excerpt in excerpts if excerpt.strip()]
        if not clean_excerpts:
            return DeckPlan(
                title=title,
                slides=(
                    SlideDraft(
                        title=f"{title}: 1",
                        body="No source excerpts were available for deterministic planning.",
                        source_excerpt=None,
                    ),
                ),
            )
        selected = clean_excerpts[: max(1, max_slides)]
        slides = tuple(
            SlideDraft(
                title=f"{title}: {index}",
                body=truncate_words(excerpt, self.words_per_slide),
                source_excerpt=excerpt,
            )
            for index, excerpt in enumerate(selected, start=1)
        )
        return DeckPlan(title=title, slides=slides)


@dataclass(frozen=True)
class OllamaProvider:
    """Small local Ollama adapter for optional live checks."""

    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 10.0

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=self.timeout_seconds)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, JSONDecodeError, ValueError):
            return []
        return sorted(str(model["name"]) for model in payload.get("models", []) if "name" in model)

    def embed(self, *, model: str, text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": text},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, JSONDecodeError, ValueError) as exc:
            raise RuntimeError("Ollama embedding failed; use deterministic fallback") from exc
        embeddings = payload.get("embeddings")
        if not embeddings:
            raise RuntimeError("Ollama did not return embeddings")
        return [float(value) for value in embeddings[0]]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(".,;:") + "..."
