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
    stockfish_path: str = "stockfish"
    stockfish_depth_default: int = 10
    stockfish_depth_max: int = 16
    analysis_max_plies: int = 300
    analysis_job_timeout_seconds: int = 120
    chesscom_sync_max_months: int = 3
    chesscom_sync_timeout_seconds: int = 120
    chesscom_user_agent: str = "ChessJU/0.1 contact: local-development"
    cors_allowed_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:8080,"
        "http://localhost:8001"
    )
    cors_allow_credentials: bool = True
    cors_allowed_methods: str = "GET,POST,PATCH,DELETE,OPTIONS"
    cors_allowed_headers: str = "Authorization,Content-Type,X-Request-ID"
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_hour: int = 10
    rate_limit_pgn_per_hour: int = 20
    rate_limit_analysis_per_hour: int = 10
    rate_limit_chesscom_sync_per_hour: int = 5
    rate_limit_message_per_minute: int = 60

    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_allowed_origins)

    def cors_method_list(self) -> list[str]:
        return _split_csv(self.cors_allowed_methods)

    def cors_header_list(self) -> list[str]:
        return _split_csv(self.cors_allowed_headers)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CHESSJU_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
