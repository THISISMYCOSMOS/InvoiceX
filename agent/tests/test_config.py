"""Environment-backed agent setting tests."""

from invoicex_agents.config import AgentSettings


def test_default_gemini_attempts_allows_one_transient_retry() -> None:
    settings = AgentSettings(_env_file=None, VERTEX_AI_PROJECT_ID="test-project")

    assert settings.gemini_max_attempts == 2
