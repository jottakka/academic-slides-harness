import pytest

from academic_slides_harness.llm.providers import OllamaProvider


@pytest.mark.ollama
def test_ollama_provider_lists_models_and_embeds_with_local_model() -> None:
    provider = OllamaProvider()
    if not provider.is_available():
        pytest.skip("Ollama server is not available")

    models = provider.list_models()
    assert models

    if "nomic-embed-text:latest" not in models:
        pytest.skip("nomic-embed-text:latest is not installed")

    embedding = provider.embed(model="nomic-embed-text:latest", text="spectral theorem")
    assert len(embedding) > 100
    assert all(isinstance(value, float) for value in embedding[:10])
