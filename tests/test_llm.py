import httpx
import pytest

from academic_slides_harness.llm.providers import NoLLMProvider, OllamaProvider


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
