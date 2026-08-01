"""Environment-backed agent setting tests."""

from invoicex_agents.config import AgentSettings


def test_default_gemini_attempts_allows_one_transient_retry() -> None:
    settings = AgentSettings(_env_file=None, GEMINI_API_KEY="test-key")

    assert settings.gemini_max_attempts == 2
