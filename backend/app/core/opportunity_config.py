from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpportunityIntelligenceSettings(BaseSettings):
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_api_url: str = "https://api.anthropic.com/v1/messages"
    anthropic_version: str = "2023-06-01"
    anthropic_max_tokens: int = Field(
        default=8192,
        ge=1024,
        le=64_000,
    )

    opportunity_fetch_timeout_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
    )
    opportunity_max_source_characters: int = Field(
        default=200_000,
        ge=10_000,
        le=2_000_000,
    )
    opportunity_max_source_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1_000_000,
    )
    opportunity_source_storage_root: Path = Path("storage/opportunity_sources")
    opportunity_max_candidates_per_role: int = Field(
        default=50,
        ge=5,
        le=500,
    )
    opportunity_default_team_options: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_opportunity_intelligence_settings() -> OpportunityIntelligenceSettings:
    return OpportunityIntelligenceSettings()
