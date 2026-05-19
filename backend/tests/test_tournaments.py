import asyncio
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.main import app
from app.tournaments.models import Tournament, TournamentRegistration

client = TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "tournament-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Tournament Test User",
    }


def register_user(prefix: str = "tournament-test") -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload(prefix))
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


def register_admin() -> dict:
    data = register_user("tournament-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def create_time_control(admin_data: dict) -> dict:
    response = client.post(
        "/api/v1/admin/time-controls",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "name": f"Rapid 10+5 {unique_suffix()}",
            "base_seconds": 600,
            "increment_seconds": 5,
            "delay_seconds": 0,
            "type": "rapid",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def tournament_payload(
    *,
    slug: str | None = None,
    title: str | None = None,
    status: str = "draft",
    max_players: int | None = 16,
    starts_in_minutes: int = 60,
) -> dict:
    suffix = unique_suffix()
    starts_at = utc_now() + timedelta(minutes=starts_in_minutes)
    payload = {
        "title": title or f"ChessJU Tournament {suffix}",
        "slug": slug,
        "description": "A test tournament.",
        "status": status,
        "format": "swiss",
        "max_players": max_players,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
        "registration_close_at": (starts_at - timedelta(minutes=10)).isoformat(),
        "location": "University of Jordan",
    }
    if slug is None:
        payload.pop("slug")
    if max_players is None:
        payload.pop("max_players")
    return payload


def create_tournament(
    admin_data: dict,
    *,
    slug: str | None = None,
    title: str | None = None,
    status: str = "draft",
    max_players: int | None = 16,
    starts_in_minutes: int = 60,
) -> dict:
    response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json=tournament_payload(
            slug=slug,
            title=title,
            status=status,
            max_players=max_players,
            starts_in_minutes=starts_in_minutes,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish_tournament(admin_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/admin/tournaments/{tournament_id}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def open_registration(admin_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/admin/tournaments/{tournament_id}/open-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def close_registration(admin_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/admin/tournaments/{tournament_id}/close-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_open_tournament(
    admin_data: dict,
    *,
    slug: str | None = None,
    max_players: int | None = 16,
    starts_in_minutes: int = 60,
) -> dict:
    tournament = create_tournament(
        admin_data,
        slug=slug,
        max_players=max_players,
        starts_in_minutes=starts_in_minutes,
    )
    publish_tournament(admin_data, tournament["id"])
    return open_registration(admin_data, tournament["id"])


def register_for_tournament(user_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/tournaments/{tournament_id}/register",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )
    assert response.status_code == 201, response.text
    return response.json()


def latest_audit_log(action: str, entity_id: str, admin_data: dict) -> dict:
    response = client.get(
        f"/api/v1/admin/audit-logs?action={action}&limit=20",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        if item["entity_id"] == entity_id:
            return item
    raise AssertionError(f"Audit log not found for {action} {entity_id}")


async def set_tournament_status_direct(tournament_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        tournament = await session.get(Tournament, uuid.UUID(tournament_id))
        assert tournament is not None
        tournament.status = status
        await session.commit()


def test_admin_can_create_time_control() -> None:
    admin_data = register_admin()
    time_control = create_time_control(admin_data)

    assert time_control["name"].startswith("Rapid 10+5")
    assert time_control["base_seconds"] == 600
    assert time_control["type"] == "rapid"


def test_member_cannot_create_time_control() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/time-controls",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json={
            "name": "Rapid 10+5",
            "base_seconds": 600,
            "increment_seconds": 5,
            "type": "rapid",
        },
    )

    assert response.status_code == 403


def test_admin_can_list_time_controls() -> None:
    admin_data = register_admin()
    create_time_control(admin_data)

    response = client.get(
        "/api/v1/admin/time-controls",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_admin_can_create_draft_tournament() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)

    assert tournament["status"] == "draft"
    assert tournament["format"] == "swiss"
    assert tournament["approved_count"] == 0


def test_member_cannot_create_tournament() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json=tournament_payload(),
    )

    assert response.status_code == 403


def test_admin_can_publish_tournament() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)

    response = publish_tournament(admin_data, tournament["id"])

    assert response["status"] == "published"


def test_admin_can_open_registration() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)
    publish_tournament(admin_data, tournament["id"])

    response = open_registration(admin_data, tournament["id"])

    assert response["status"] == "registration_open"
    assert response["registration_open_at"] is not None


def test_admin_can_close_registration() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data)

    response = close_registration(admin_data, tournament["id"])

    assert response["status"] == "registration_closed"
    assert response["registration_close_at"] is not None


def test_admin_can_cancel_tournament() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)

    response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/cancel",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_admin_can_soft_delete_tournament() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)

    response = client.delete(
        f"/api/v1/admin/tournaments/{tournament['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": True}


def test_admin_tournament_mutation_creates_audit_log() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data)

    response = client.patch(
        f"/api/v1/admin/tournaments/{tournament['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"location": "Updated Room"},
    )
    log = latest_audit_log("tournament.updated", tournament["id"], admin_data)

    assert response.status_code == 200
    assert log["before"]["location"] == "University of Jordan"
    assert log["after"]["location"] == "Updated Room"


def test_duplicate_generated_slug_is_handled_safely() -> None:
    admin_data = register_admin()
    title = f"Duplicate Tournament {unique_suffix()}"
    first = create_tournament(admin_data, title=title)
    second = create_tournament(admin_data, title=title)

    assert first["slug"] != second["slug"]
    assert second["slug"].startswith(first["slug"])


def test_public_list_does_not_show_draft_tournaments() -> None:
    admin_data = register_admin()
    tournament = create_tournament(admin_data, slug=f"draft-{unique_suffix()}")

    response = client.get("/api/v1/tournaments?limit=100")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["items"]}
    assert tournament["slug"] not in slugs


def test_public_list_shows_registration_open_tournament() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(
        admin_data,
        slug=f"public-open-{unique_suffix()}",
        starts_in_minutes=5,
    )

    response = client.get("/api/v1/tournaments?status=registration_open&limit=100")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["items"]}
    assert tournament["slug"] in slugs


def test_public_detail_returns_tournament_by_slug() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data, slug=f"detail-{unique_suffix()}")

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == tournament["id"]
    assert body["approved_count"] == 0
    assert body["my_registration"] is None


def test_public_detail_404s_for_draft_or_deleted_tournament() -> None:
    admin_data = register_admin()
    draft = create_tournament(admin_data, slug=f"hidden-draft-{unique_suffix()}")
    deleted = create_open_tournament(admin_data, slug=f"hidden-deleted-{unique_suffix()}")
    client.delete(
        f"/api/v1/admin/tournaments/{deleted['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    draft_response = client.get(f"/api/v1/tournaments/{draft['slug']}")
    deleted_response = client.get(f"/api/v1/tournaments/{deleted['slug']}")

    assert draft_response.status_code == 404
    assert deleted_response.status_code == 404


def test_authenticated_member_can_register_for_registration_open_tournament() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)

    registration = register_for_tournament(member_data, tournament["id"])

    assert registration["status"] == "approved"
    assert registration["user_id"] == member_data["user"]["id"]


def test_unauthenticated_user_cannot_register() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data)

    response = client.post(f"/api/v1/tournaments/{tournament['id']}/register")

    assert response.status_code == 401


def test_user_cannot_register_twice() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    register_for_tournament(member_data, tournament["id"])

    response = client.post(
        f"/api/v1/tournaments/{tournament['id']}/register",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )

    assert response.status_code == 409


def test_user_cannot_register_for_draft_tournament() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_tournament(admin_data)

    response = client.post(
        f"/api/v1/tournaments/{tournament['id']}/register",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )

    assert response.status_code == 400


def test_user_cannot_register_for_closed_cancelled_or_completed_tournament() -> None:
    admin_data = register_admin()
    member_data = register_user()
    closed = create_open_tournament(admin_data)
    close_registration(admin_data, closed["id"])
    cancelled = create_open_tournament(admin_data)
    client.post(
        f"/api/v1/admin/tournaments/{cancelled['id']}/cancel",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    completed = create_open_tournament(admin_data)
    asyncio.run(set_tournament_status_direct(completed["id"], "completed"))

    for tournament in (closed, cancelled, completed):
        response = client.post(
            f"/api/v1/tournaments/{tournament['id']}/register",
            headers=auth_headers(member_data["tokens"]["access_token"]),
        )
        assert response.status_code == 400


def test_capacity_available_registration_is_approved() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data, max_players=2)

    registration = register_for_tournament(member_data, tournament["id"])

    assert registration["status"] == "approved"


def test_capacity_full_registration_is_waitlisted() -> None:
    admin_data = register_admin()
    first_member = register_user()
    second_member = register_user()
    tournament = create_open_tournament(admin_data, max_players=1)
    first = register_for_tournament(first_member, tournament["id"])
    second = register_for_tournament(second_member, tournament["id"])

    assert first["status"] == "approved"
    assert second["status"] == "waitlisted"


def test_user_can_cancel_own_registration() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    register_for_tournament(member_data, tournament["id"])

    response = client.delete(
        f"/api/v1/tournaments/{tournament['id']}/registration",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancelled_at"] is not None


def test_registration_cancellation_rejects_already_cancelled_registration() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    register_for_tournament(member_data, tournament["id"])
    client.delete(
        f"/api/v1/tournaments/{tournament['id']}/registration",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )

    response = client.delete(
        f"/api/v1/tournaments/{tournament['id']}/registration",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )

    assert response.status_code == 409


def test_admin_can_list_tournament_registrations() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    registration = register_for_tournament(member_data, tournament["id"])

    response = client.get(
        f"/api/v1/admin/tournaments/{tournament['id']}/registrations",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert registration["id"] in ids


def test_admin_can_update_registration_status() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    registration = register_for_tournament(member_data, tournament["id"])

    response = client.patch(
        f"/api/v1/admin/tournament-registrations/{registration['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"status": "rejected", "seed_rating": 1200},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["seed_rating"] == 1200


async def _assert_duplicate_registration_violates_unique(
    tournament_id: str, user_id: str
) -> None:
    async with AsyncSessionLocal() as session:
        duplicate = TournamentRegistration(
            tournament_id=uuid.UUID(tournament_id),
            user_id=uuid.UUID(user_id),
            status="approved",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


def test_registration_uniqueness_is_enforced_by_database() -> None:
    admin_data = register_admin()
    member_data = register_user()
    tournament = create_open_tournament(admin_data)
    register_for_tournament(member_data, tournament["id"])

    asyncio.run(
        _assert_duplicate_registration_violates_unique(
            tournament_id=tournament["id"],
            user_id=member_data["user"]["id"],
        )
    )


def test_home_includes_upcoming_tournaments() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(
        admin_data,
        slug=f"home-open-{unique_suffix()}",
        starts_in_minutes=2,
    )

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["upcoming_tournaments"]}
    assert tournament["slug"] in slugs


def test_home_excludes_draft_cancelled_completed_and_deleted_tournaments() -> None:
    admin_data = register_admin()
    draft = create_tournament(admin_data, slug=f"home-draft-{unique_suffix()}", starts_in_minutes=2)
    cancelled = create_open_tournament(
        admin_data,
        slug=f"home-cancelled-{unique_suffix()}",
        starts_in_minutes=2,
    )
    client.post(
        f"/api/v1/admin/tournaments/{cancelled['id']}/cancel",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    completed = create_open_tournament(
        admin_data,
        slug=f"home-completed-{unique_suffix()}",
        starts_in_minutes=2,
    )
    asyncio.run(set_tournament_status_direct(completed["id"], "completed"))
    deleted = create_open_tournament(
        admin_data,
        slug=f"home-deleted-{unique_suffix()}",
        starts_in_minutes=2,
    )
    client.delete(
        f"/api/v1/admin/tournaments/{deleted['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["upcoming_tournaments"]}
    assert draft["slug"] not in slugs
    assert cancelled["slug"] not in slugs
    assert completed["slug"] not in slugs
    assert deleted["slug"] not in slugs


def test_home_keeps_leaderboard_preview_empty() -> None:
    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["leaderboard_preview"] == []
