"""Environment-backed configuration for Gemini clients."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    vertex_ai_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VERTEX_AI_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID"),
    )
    vertex_ai_location: str = Field(
        default="global",
        validation_alias="VERTEX_AI_LOCATION",
        min_length=1,
    )
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        validation_alias="GEMINI_MODEL",
        min_length=1,
    )
    gemini_timeout_seconds: float = Field(
        default=180,
        validation_alias="GEMINI_TIMEOUT_SECONDS",
        gt=0,
        le=300,
    )
    gemini_max_attempts: int = Field(
        default=2,
        validation_alias="GEMINI_MAX_ATTEMPTS",
        ge=1,
        le=3,
    )
