from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ChessJU API"}


def test_version_endpoint() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["app_name"] == "ChessJU API"
    assert response.json()["version"] == "0.1.0"


def test_database_health_success(monkeypatch) -> None:
    async def fake_database_check() -> bool:
        return True

    monkeypatch.setattr("app.main.check_database_connection", fake_database_check)

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "postgresql"}


def test_database_health_failure(monkeypatch) -> None:
    async def fake_database_check() -> bool:
        return False

    monkeypatch.setattr("app.main.check_database_connection", fake_database_check)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"] == {"status": "unavailable", "database": "postgresql"}
