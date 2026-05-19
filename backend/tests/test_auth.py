import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def unique_user_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:12]
    return {
        "email": f"user-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"user_{suffix}",
        "full_name": "ChessJU Member",
        "university_id": f"UJ-{suffix}",
        "chesscom_username": f"chessju_{suffix}",
    }


def register_user(payload: dict[str, str] | None = None) -> tuple[dict[str, str], dict]:
    request_payload = payload or unique_user_payload()
    response = client.post("/api/v1/auth/register", json=request_payload)
    assert response.status_code == 201, response.text
    return request_payload, response.json()


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_register_user_successfully() -> None:
    payload, data = register_user()

    assert data["user"]["email"] == payload["email"]
    assert data["user"]["profile"]["username"] == payload["username"]
    assert data["user"]["profile"]["full_name"] == payload["full_name"]
    assert data["user"]["preferences"]["app_theme"] == "system"
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]


def test_register_duplicate_email_fails() -> None:
    payload, _ = register_user()
    duplicate_payload = unique_user_payload()
    duplicate_payload["email"] = payload["email"]

    response = client.post("/api/v1/auth/register", json=duplicate_payload)

    assert response.status_code == 409


def test_register_duplicate_username_fails() -> None:
    payload, _ = register_user()
    duplicate_payload = unique_user_payload()
    duplicate_payload["username"] = payload["username"]

    response = client.post("/api/v1/auth/register", json=duplicate_payload)

    assert response.status_code == 409


def test_login_with_correct_password_succeeds() -> None:
    payload, _ = register_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert response.status_code == 200
    assert response.json()["tokens"]["access_token"]


def test_login_with_wrong_password_fails() -> None:
    payload, _ = register_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_auth_me_requires_token() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_auth_me_returns_current_user() -> None:
    payload, data = register_user()
    access_token = data["tokens"]["access_token"]

    response = client.get("/api/v1/auth/me", headers=auth_headers(access_token))

    assert response.status_code == 200
    assert response.json()["email"] == payload["email"]


def test_refresh_token_returns_new_access_token() -> None:
    _, data = register_user()

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["tokens"]["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


def test_logout_revokes_refresh_token() -> None:
    _, data = register_user()
    refresh_token = data["tokens"]["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert logout_response.status_code == 200
    assert logout_response.json() == {"revoked": True}
    assert refresh_response.status_code == 401


def test_new_user_receives_member_role() -> None:
    _, data = register_user()

    assert "member" in data["user"]["roles"]


def test_user_can_update_own_profile() -> None:
    _, data = register_user()
    access_token = data["tokens"]["access_token"]
    new_username = f"updated_{uuid.uuid4().hex[:10]}"

    response = client.patch(
        "/api/v1/users/me/profile",
        headers=auth_headers(access_token),
        json={
            "username": new_username,
            "full_name": "Updated ChessJU Member",
            "chesscom_username": "updated_chessju",
        },
    )

    assert response.status_code == 200
    assert response.json()["username"] == new_username
    assert response.json()["full_name"] == "Updated ChessJU Member"


def test_user_can_update_own_preferences() -> None:
    _, data = register_user()
    access_token = data["tokens"]["access_token"]

    response = client.patch(
        "/api/v1/users/me/preferences",
        headers=auth_headers(access_token),
        json={
            "app_theme": "dark",
            "board_theme": "green",
            "clock_sound_enabled": False,
            "language": "ar",
            "notification_settings": {"announcements": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["app_theme"] == "dark"
    assert response.json()["board_theme"] == "green"
    assert response.json()["clock_sound_enabled"] is False
    assert response.json()["language"] == "ar"
    assert response.json()["notification_settings"] == {"announcements": True}
