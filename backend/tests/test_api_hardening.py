import uuid

from fastapi.testclient import TestClient

from app.common import rate_limit as rate_limit_module
from app.common.rate_limit import InMemoryRateLimiter
from app.common.request_context import REQUEST_ID_HEADER
from app.config import get_settings
from app.main import app

client = TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def unique_user_payload(prefix: str = "hardening-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Hardening Test User",
    }


def register_user() -> tuple[dict[str, str], dict]:
    payload = unique_user_payload()
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload, response.json()


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def assert_error_shape(response, expected_code: str) -> None:
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == expected_code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], dict)
    assert body["error"]["request_id"]
    assert response.headers[REQUEST_ID_HEADER] == body["error"]["request_id"]
    assert "traceback" not in response.text.lower()


def test_401_response_uses_standard_error_shape() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert_error_shape(response, "auth.unauthorized")


def test_403_response_uses_standard_error_shape() -> None:
    _, data = register_user()

    response = client.get(
        "/api/v1/admin/me",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 403
    assert_error_shape(response, "auth.forbidden")


def test_404_response_uses_standard_error_shape() -> None:
    response = client.get(f"/api/v1/news/missing-{unique_suffix()}")

    assert response.status_code == 404
    assert_error_shape(response, "resource.not_found")


def test_validation_response_uses_standard_error_shape() -> None:
    response = client.post("/api/v1/auth/register", json={"email": "not-an-email"})

    assert response.status_code == 422
    assert_error_shape(response, "validation.invalid_input")
    assert response.json()["error"]["details"]["errors"]


def test_request_id_header_is_added_and_preserves_safe_input() -> None:
    request_id = f"flutter-smoke-{unique_suffix()}"

    response = client.get("/health", headers={REQUEST_ID_HEADER: request_id})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == request_id


def test_cors_allows_configured_localhost_origin() -> None:
    response = client.options(
        "/api/v1/home",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_pagination_limit_and_offset_validation() -> None:
    limit_response = client.get("/api/v1/news?limit=101")
    offset_response = client.get("/api/v1/news?offset=-1")
    valid_response = client.get("/api/v1/news?limit=1&offset=0")

    assert limit_response.status_code == 422
    assert_error_shape(limit_response, "validation.invalid_input")
    assert offset_response.status_code == 422
    assert_error_shape(offset_response, "validation.invalid_input")
    assert valid_response.status_code == 200
    assert {"items", "limit", "offset", "total"}.issubset(valid_response.json())


def test_valkey_health_success_and_failure(monkeypatch) -> None:
    async def healthy() -> bool:
        return True

    async def unhealthy() -> bool:
        return False

    monkeypatch.setattr("app.main.check_valkey_connection", healthy)
    success_response = client.get("/health/valkey")
    monkeypatch.setattr("app.main.check_valkey_connection", unhealthy)
    failure_response = client.get("/health/valkey")

    assert success_response.status_code == 200
    assert success_response.json() == {"status": "ok", "valkey": "valkey"}
    assert failure_response.status_code == 503
    assert_error_shape(failure_response, "service.unavailable")


def test_rate_limit_allows_then_blocks_with_standard_error(monkeypatch) -> None:
    payload, _ = register_user()
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_login_per_minute", 1)
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr(rate_limit_module, "get_rate_limiter", lambda: limiter)

    first = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    second = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert_error_shape(second, "rate_limit.exceeded")


def test_disabled_rate_limit_bypasses_limiter(monkeypatch) -> None:
    payload, _ = register_user()
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_login_per_minute", 0)
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr(rate_limit_module, "get_rate_limiter", lambda: limiter)

    first = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    second = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
