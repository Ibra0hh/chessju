import asyncio
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admin.models import AdminActionLog
from app.admin.services import REDACTED_VALUE, create_admin_action_log
from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.main import app

client = TestClient(app)


def unique_user_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:12]
    return {
        "email": f"admin-test-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"admintest_{suffix}",
        "full_name": "Admin Test User",
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_user() -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload())
    assert response.status_code == 201, response.text
    return response.json()


async def _assign_role(user_id: uuid.UUID, role_name: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one()
        session.add(UserRole(user_id=user_id, role_id=role.id))
        await session.commit()


def assign_role(user_id: str, role_name: str) -> None:
    asyncio.run(_assign_role(uuid.UUID(user_id), role_name))


def register_admin(role_name: str = "admin") -> dict:
    data = register_user()
    assign_role(data["user"]["id"], role_name)
    return data


async def _create_log(
    admin_id: uuid.UUID,
    action: str,
    entity_type: str = "test_entity",
    created_offset_seconds: int = 0,
    before: dict | None = None,
    after: dict | None = None,
) -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        log = await create_admin_action_log(
            db=session,
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=uuid.uuid4(),
            before=before,
            after=after,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        log.created_at = utc_now() + timedelta(seconds=created_offset_seconds)
        await session.commit()
        return log.id


def create_log(
    admin_id: str,
    action: str,
    entity_type: str = "test_entity",
    created_offset_seconds: int = 0,
    before: dict | None = None,
    after: dict | None = None,
) -> uuid.UUID:
    return asyncio.run(
        _create_log(
            admin_id=uuid.UUID(admin_id),
            action=action,
            entity_type=entity_type,
            created_offset_seconds=created_offset_seconds,
            before=before,
            after=after,
        )
    )


def test_member_cannot_access_admin_me() -> None:
    data = register_user()

    response = client.get(
        "/api/v1/admin/me",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 403


def test_admin_can_access_admin_me() -> None:
    data = register_admin("admin")

    response = client.get(
        "/api/v1/admin/me",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["email"] == data["user"]["email"]
    assert "admin" in response.json()["roles"]


def test_super_admin_can_access_admin_me() -> None:
    data = register_admin("super_admin")

    response = client.get(
        "/api/v1/admin/me",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert "super_admin" in response.json()["roles"]


def test_member_cannot_list_audit_logs() -> None:
    data = register_user()

    response = client.get(
        "/api/v1/admin/audit-logs",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 403


def test_admin_can_list_audit_logs() -> None:
    data = register_admin("admin")
    create_log(data["user"]["id"], action="admin.test.list")

    response = client.get(
        "/api/v1/admin/audit-logs",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"]


def test_audit_log_service_creates_log() -> None:
    data = register_admin("admin")
    log_id = create_log(data["user"]["id"], action="admin.test.create")

    async def load_log() -> AdminActionLog:
        async with AsyncSessionLocal() as session:
            log = await session.get(AdminActionLog, log_id)
            assert log is not None
            return log

    log = asyncio.run(load_log())

    assert log.admin_id == uuid.UUID(data["user"]["id"])
    assert log.action == "admin.test.create"
    assert log.entity_type == "test_entity"


def test_audit_log_list_supports_pagination() -> None:
    data = register_admin("admin")
    create_log(data["user"]["id"], action="admin.test.page", created_offset_seconds=1)
    create_log(data["user"]["id"], action="admin.test.page", created_offset_seconds=2)
    create_log(data["user"]["id"], action="admin.test.page", created_offset_seconds=3)

    response = client.get(
        "/api/v1/admin/audit-logs?action=admin.test.page&limit=2&offset=1",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["limit"] == 2
    assert response.json()["offset"] == 1
    assert len(response.json()["items"]) == 2
    assert response.json()["total"] >= 3


def test_audit_log_list_sorts_newest_first() -> None:
    data = register_admin("admin")
    old_log_id = create_log(data["user"]["id"], action="admin.test.sort", created_offset_seconds=1)
    new_log_id = create_log(data["user"]["id"], action="admin.test.sort", created_offset_seconds=10)

    response = client.get(
        "/api/v1/admin/audit-logs?action=admin.test.sort&limit=2",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == str(new_log_id)
    assert items[1]["id"] == str(old_log_id)


def test_audit_log_response_does_not_expose_sensitive_fields() -> None:
    data = register_admin("admin")
    create_log(
        data["user"]["id"],
        action="admin.test.sensitive",
        before={"password": "plain", "safe": "before"},
        after={
            "password_hash": "hash",
            "refresh_token": "refresh",
            "nested": {"token_hash": "token-hash", "safe": "ok"},
            "items": [{"authorization": "Bearer secret"}],
        },
    )

    response = client.get(
        "/api/v1/admin/audit-logs?action=admin.test.sensitive&limit=1",
        headers=auth_headers(data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    body = response.json()["items"][0]
    assert body["before"]["password"] == REDACTED_VALUE
    assert body["after"]["password_hash"] == REDACTED_VALUE
    assert body["after"]["refresh_token"] == REDACTED_VALUE
    assert body["after"]["nested"]["token_hash"] == REDACTED_VALUE
    assert body["after"]["nested"]["safe"] == "ok"
    assert body["after"]["items"][0]["authorization"] == REDACTED_VALUE
    assert "plain" not in response.text
    assert "token-hash" not in response.text
    assert "Bearer secret" not in response.text
