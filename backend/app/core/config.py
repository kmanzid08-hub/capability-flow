from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Capability Flow API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://capability_flow:capability_flow@localhost:5432/capability_flow"
    )
    jwt_secret_key: str = Field(
        default="development-only-change-this-secret-key",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]

    storage_backend: Literal["local", "r2"] = "local"

    document_storage_path: Path = Path("storage/documents")
    document_max_file_size_mb: int = Field(
        default=25,
        ge=1,
        le=250,
    )

    r2_endpoint_url: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None

    ai_provider: Literal["anthropic"] = "anthropic"
    anthropic_api_key: str | None = None
    ai_model: str = "claude-sonnet-4-20250514"
    ai_max_document_chars: int = Field(default=120_000, ge=10_000, le=500_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "database_url",
        mode="before",
    )
    @classmethod
    def normalize_postgres_driver(
        cls,
        value: object,
    ) -> object:
        if not isinstance(value, str):
            return value

        if value.startswith(
            "postgresql+psycopg://",
        ):
            return value

        if value.startswith(
            "postgresql://",
        ):
            return value.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        if value.startswith(
            "postgres://",
        ):
            return value.replace(
                "postgres://",
                "postgresql+psycopg://",
                1,
            )

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
