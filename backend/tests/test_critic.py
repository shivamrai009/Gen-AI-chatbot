from app.models.schemas import Source
from app.services.critic import CriticService


def test_critic_passes_fallback_answer() -> None:
    critic = CriticService()
    result = critic.evaluate("Gemini API key is not configured.", [])
    assert result.passed


def test_critic_fails_without_sources_for_normal_answer() -> None:
    critic = CriticService()
    result = critic.evaluate("GitLab does X and Y.", [])
    assert not result.passed


def test_critic_passes_grounded_overlap() -> None:
    critic = CriticService()
    answer = "The handbook provides public guidance for GitLab teams."
    sources = [
        Source(
            title="The GitLab Handbook",
            url="https://handbook.gitlab.com",
            snippet="The handbook is a public source of guidance for teams.",
            section="General",
        )
    ]
    result = critic.evaluate(answer, sources)
    assert result.passed
