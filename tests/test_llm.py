from academic_slides_harness.llm.providers import NoLLMProvider


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
