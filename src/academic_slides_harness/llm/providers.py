from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import re
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Protocol

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


def discover_model_providers(
    *,
    ollama_base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: float = 1.0,
) -> dict[str, Any]:
    """Return redacted local/model provider availability for agent routing."""
    ollama = OllamaProvider(base_url=ollama_base_url, timeout_seconds=timeout_seconds)
    ollama_available = ollama.is_available()
    ollama_models = sorted(ollama.list_models()) if ollama_available else []
    vision_candidates = [model for model in ollama_models if _is_vision_model_candidate(model)]
    embedding_candidates = [
        model for model in ollama_models if _is_embedding_model_candidate(model)
    ]
    ollama_warnings: list[str] = []
    if ollama_available and ollama_models and not vision_candidates:
        ollama_warnings.append("no_likely_vision_model")

    return {
        "ollama": {
            "available": ollama_available,
            "base_url": ollama_base_url,
            "models": ollama_models,
            "vision_model_candidates": vision_candidates,
            "embedding_model_candidates": embedding_candidates,
            "warnings": ollama_warnings,
        },
        "openai": _openai_config_report(),
        "azure_openai": _azure_openai_config_report(),
        "markitdown": _package_report(
            module_name="markitdown",
            distribution_name="markitdown",
            extras=["pdf", "docx", "pptx", "xlsx"],
        )
        | {
            "ocr_plugin_available": _package_available("markitdown_ocr"),
        },
    }


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(".,;:") + "..."


def _openai_config_report() -> dict[str, Any]:
    env_vars = [
        name
        for name in [
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
        ]
        if os.environ.get(name)
    ]
    return {
        "api_key_configured": "OPENAI_API_KEY" in env_vars,
        "base_url_configured": "OPENAI_BASE_URL" in env_vars,
        "configured_env_vars": env_vars,
    }


def _azure_openai_config_report() -> dict[str, Any]:
    env_vars = [
        name
        for name in [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
        ]
        if os.environ.get(name)
    ]
    return {
        "api_key_configured": "AZURE_OPENAI_API_KEY" in env_vars,
        "endpoint_configured": "AZURE_OPENAI_ENDPOINT" in env_vars,
        "configured_env_vars": env_vars,
    }


def _package_report(
    *,
    module_name: str,
    distribution_name: str,
    extras: list[str],
) -> dict[str, Any]:
    available = _package_available(module_name)
    return {
        "available": available,
        "version": _package_version(distribution_name) if available else None,
        "recommended_extras": extras,
    }


def _package_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _package_version(distribution_name: str) -> str | None:
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _is_vision_model_candidate(model_name: str) -> bool:
    normalized = model_name.lower()
    tokens = [
        "llava",
        "bakllava",
        "moondream",
        "minicpm-v",
        "minicpm-vl",
        "qwen-vl",
        "qwen2-vl",
        "qwen2.5-vl",
        "qwen2.5vl",
        "vision",
    ]
    return any(token in normalized for token in tokens)


def _is_embedding_model_candidate(model_name: str) -> bool:
    normalized = model_name.lower()
    tokens = [
        "embed",
        "embedding",
        "nomic-embed",
        "mxbai-embed",
        "bge",
        "all-minilm",
    ]
    return any(token in normalized for token in tokens)
