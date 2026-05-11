import json

import httpx
import pytest

from academic_slides_harness.llm.providers import (
    NoLLMProvider,
    OllamaProvider,
    discover_model_providers,
)


def test_no_llm_provider_creates_deterministic_deck_plan() -> None:
    provider = NoLLMProvider()

    plan = provider.plan_deck(
        title="Spectral Theorem",
        excerpts=[
            "The spectral theorem gives conditions for diagonalizing operators.",
            "Orthogonal eigenvectors simplify quadratic forms.",
        ],
        max_slides=2,
    )

    assert plan.title == "Spectral Theorem"
    assert len(plan.slides) == 2
    assert plan.slides[0].title == "Spectral Theorem: 1"
    assert "spectral theorem" in plan.slides[0].body.lower()


def test_no_llm_provider_returns_explanatory_slide_for_empty_excerpts() -> None:
    provider = NoLLMProvider()

    plan = provider.plan_deck(title="Empty Source", excerpts=["  "], max_slides=3)

    assert len(plan.slides) == 1
    assert plan.slides[0].title == "Empty Source: 1"
    assert "No source excerpts" in plan.slides[0].body


def test_ollama_provider_list_models_degrades_to_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_get(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("academic_slides_harness.llm.providers.httpx.get", fail_get)

    assert OllamaProvider().list_models() == []


def test_ollama_provider_embed_wraps_http_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_post(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr("academic_slides_harness.llm.providers.httpx.post", fail_post)

    with pytest.raises(RuntimeError, match="Ollama embedding failed"):
        OllamaProvider().embed(model="nomic-embed-text", text="hello")


def test_discover_model_providers_redacts_configured_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_key = "sk-proj-" + ("x" * 48)
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", fake_key)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid")
    monkeypatch.setattr(OllamaProvider, "is_available", lambda _self: False)
    monkeypatch.setattr(OllamaProvider, "list_models", lambda _self: [])

    report = discover_model_providers()
    raw_report = json.dumps(report)

    assert fake_key not in raw_report
    assert report["openai"]["api_key_configured"] is True
    assert report["openai"]["base_url_configured"] is True
    assert report["openai"]["configured_env_vars"] == ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert report["azure_openai"]["api_key_configured"] is True
    assert report["azure_openai"]["endpoint_configured"] is True
    assert report["azure_openai"]["configured_env_vars"] == [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
    ]


def test_discover_model_providers_lists_ollama_model_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda _self: True)
    monkeypatch.setattr(
        OllamaProvider,
        "list_models",
        lambda _self: ["qwen2.5-coder:7b", "llava:latest", "nomic-embed-text:latest"],
    )

    report = discover_model_providers()

    assert report["ollama"]["available"] is True
    assert report["ollama"]["models"] == [
        "llava:latest",
        "nomic-embed-text:latest",
        "qwen2.5-coder:7b",
    ]
    assert report["ollama"]["vision_model_candidates"] == ["llava:latest"]
    assert report["ollama"]["embedding_model_candidates"] == ["nomic-embed-text:latest"]
    assert report["ollama"]["warnings"] == []


def test_discover_model_providers_warns_when_no_vision_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(OllamaProvider, "is_available", lambda _self: True)
    monkeypatch.setattr(OllamaProvider, "list_models", lambda _self: ["qwen2.5-coder:7b"])

    report = discover_model_providers()

    assert report["ollama"]["available"] is True
    assert report["ollama"]["vision_model_candidates"] == []
    assert "no_likely_vision_model" in report["ollama"]["warnings"]
