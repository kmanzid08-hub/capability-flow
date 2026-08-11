from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Capability Flow API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://capability_flow:capability_flow@localhost:5432/capability_flow"
    )
    jwt_secret_key: str = Field(default="development-only-change-this-secret-key", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
