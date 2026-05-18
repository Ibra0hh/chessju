from app.config import Settings


def test_default_settings() -> None:
    settings = Settings()

    assert settings.app_name == "ChessJU API"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url.startswith("postgresql+psycopg://")
