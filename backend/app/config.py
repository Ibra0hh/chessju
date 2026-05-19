from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChessJU API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://chessju:chessju_dev_password@postgres:5432/chessju"
    )
    valkey_url: str = "redis://valkey:6379/0"
    local_storage_root: str = "/data/storage"

    jwt_secret_key: str = "change-me-in-local-development-secret-32-plus"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CHESSJU_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
