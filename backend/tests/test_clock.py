import asyncio
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import Role, UserRole
from app.clock.models import ClockEvent
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.main import app
from app.tournaments.models import Tournament

client = TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "clock-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Clock Test User",
    }


def register_user(prefix: str = "clock-test") -> dict:
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
    data = register_user("clock-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def create_casual_clock(user_data: dict) -> dict:
    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={
            "base_seconds": 300,
            "increment_seconds": 3,
            "delay_seconds": 0,
            "white_user_id": user_data["user"]["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def snapshot_payload(
    white_remaining_ms: int = 300_000,
    black_remaining_ms: int = 300_000,
) -> dict:
    return {
        "white_remaining_ms": white_remaining_ms,
        "black_remaining_ms": black_remaining_ms,
    }


def start_clock(user_data: dict, clock_session_id: str) -> dict:
    response = client.post(
        f"/api/v1/clock/sessions/{clock_session_id}/start",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(), "active_color": "white"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def pause_clock(user_data: dict, clock_session_id: str) -> dict:
    response = client.post(
        f"/api/v1/clock/sessions/{clock_session_id}/pause",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json=snapshot_payload(297_000, 300_000),
    )
    assert response.status_code == 200, response.text
    return response.json()


def resume_clock(user_data: dict, clock_session_id: str) -> dict:
    response = client.post(
        f"/api/v1/clock/sessions/{clock_session_id}/resume",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(297_000, 300_000), "active_color": "white"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_time_control(admin_data: dict) -> dict:
    response = client.post(
        "/api/v1/admin/time-controls",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "name": f"Clock Rapid {unique_suffix()}",
            "base_seconds": 300,
            "increment_seconds": 3,
            "delay_seconds": 0,
            "type": "blitz",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_open_tournament(admin_data: dict) -> dict:
    starts_at = utc_now() + timedelta(days=10)
    response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "title": f"Clock Tournament {unique_suffix()}",
            "description": "Clock phase tournament.",
            "status": "draft",
            "format": "swiss",
            "time_control_id": create_time_control(admin_data)["id"],
            "max_players": 8,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
            "registration_close_at": (starts_at - timedelta(hours=1)).isoformat(),
            "location": "University of Jordan",
        },
    )
    assert response.status_code == 201, response.text
    tournament = response.json()
    client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    open_response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/open-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert open_response.status_code == 200, open_response.text
    return open_response.json()


def register_for_tournament(user_data: dict, tournament_id: str) -> None:
    response = client.post(
        f"/api/v1/tournaments/{tournament_id}/register",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )
    assert response.status_code == 201, response.text


def create_pairing_fixture() -> tuple[dict, dict, dict, dict, dict]:
    admin = register_admin()
    white = register_user("clock-white")
    black = register_user("clock-black")
    tournament = create_open_tournament(admin)
    register_for_tournament(white, tournament["id"])
    register_for_tournament(black, tournament["id"])
    round_response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/rounds",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={"round_number": 1, "title": "Round 1"},
    )
    assert round_response.status_code == 201, round_response.text
    pairing_response = client.post(
        f"/api/v1/admin/rounds/{round_response.json()['id']}/pairings",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": white["user"]["id"],
            "black_user_id": black["user"]["id"],
        },
    )
    assert pairing_response.status_code == 201, pairing_response.text
    return admin, white, black, tournament, pairing_response.json()


def create_official_clock(admin: dict, pairing: dict) -> dict:
    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={
            "pairing_id": pairing["id"],
            "base_seconds": 300,
            "increment_seconds": 3,
            "delay_seconds": 0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def event_count(clock_session_id: str) -> int:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ClockEvent)
            .where(ClockEvent.clock_session_id == uuid.UUID(clock_session_id))
        )
        return count or 0


async def set_tournament_status(tournament_id: str, next_status: str) -> None:
    async with AsyncSessionLocal() as session:
        tournament = await session.get(Tournament, uuid.UUID(tournament_id))
        assert tournament is not None
        tournament.status = next_status
        await session.commit()


def test_authenticated_user_can_create_casual_clock_session() -> None:
    user_data = register_user()

    clock = create_casual_clock(user_data)

    assert clock["status"] == "setup"
    assert clock["active_color"] == "none"
    assert clock["white_remaining_ms"] == 300_000
    assert clock["black_remaining_ms"] == 300_000


def test_unauthenticated_user_cannot_create_clock_session() -> None:
    response = client.post("/api/v1/clock/sessions", json={"base_seconds": 300})

    assert response.status_code == 401


def test_invalid_base_seconds_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"base_seconds": 0},
    )

    assert response.status_code == 422


def test_invalid_increment_and_delay_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"base_seconds": 300, "increment_seconds": -1, "delay_seconds": -1},
    )

    assert response.status_code == 422


def test_creator_can_view_casual_session() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == clock["id"]


def test_another_member_cannot_view_private_casual_session() -> None:
    owner = register_user("clock-owner")
    other = register_user("clock-other")
    clock = create_casual_clock(owner)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_admin_can_view_any_session() -> None:
    owner = register_user("clock-owner")
    admin = register_admin()
    clock = create_casual_clock(owner)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert response.status_code == 200


def test_pairing_players_can_view_pairing_linked_session() -> None:
    admin, white, _, _, pairing = create_pairing_fixture()
    clock = create_official_clock(admin, pairing)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(white["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["pairing_id"] == pairing["id"]


def test_member_cannot_create_official_pairing_session() -> None:
    admin, white, _, _, pairing = create_pairing_fixture()
    _ = admin

    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(white["tokens"]["access_token"]),
        json={"pairing_id": pairing["id"], "base_seconds": 300},
    )

    assert response.status_code == 403


def test_start_from_setup_works() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    started = start_clock(user_data, clock["id"])

    assert started["status"] == "running"
    assert started["active_color"] == "white"
    assert started["started_at"] is not None


def test_pause_from_running_works() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])

    paused = pause_clock(user_data, clock["id"])

    assert paused["status"] == "paused"
    assert paused["white_remaining_ms"] == 297_000


def test_resume_from_paused_works() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])
    pause_clock(user_data, clock["id"])

    resumed = resume_clock(user_data, clock["id"])

    assert resumed["status"] == "running"
    assert resumed["active_color"] == "white"


def test_switch_turn_works_from_running() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/switch-turn",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(297_000, 300_000), "active_color": "black"},
    )

    assert response.status_code == 200
    assert response.json()["active_color"] == "black"


def test_switch_turn_rejected_when_not_running() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/switch-turn",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(), "active_color": "black"},
    )

    assert response.status_code == 400


def test_adjust_time_works_for_authorized_user() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/adjust",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(310_000, 300_000), "reason": "correction"},
    )

    assert response.status_code == 200
    assert response.json()["white_remaining_ms"] == 310_000


def test_flag_completes_session() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/flag",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(0, 120_000), "flagged_color": "white"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"] == "white_flagged"


def test_complete_sets_status_completed() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/complete",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(), "result": "draw"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"] == "draw"


def test_reset_returns_session_to_setup() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/reset",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "setup"
    assert response.json()["active_color"] == "none"
    assert response.json()["white_remaining_ms"] == 300_000


def test_cancel_sets_status_cancelled() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/cancel",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={**snapshot_payload(), "reason": "aborted"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_invalid_transition_rejected() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/pause",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json=snapshot_payload(),
    )

    assert response.status_code == 400


def test_every_mutation_creates_clock_event() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    before = asyncio.run(event_count(clock["id"]))

    start_clock(user_data, clock["id"])

    assert before == 1
    assert asyncio.run(event_count(clock["id"])) == 2


def test_event_log_returns_ordered_events() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])
    pause_clock(user_data, clock["id"])

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}/events",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    event_types = [item["event_type"] for item in response.json()["items"]]
    assert event_types == ["setup", "start", "pause"]


def test_event_log_is_view_protected() -> None:
    owner = register_user("clock-owner")
    other = register_user("clock-other")
    clock = create_casual_clock(owner)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}/events",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_event_stores_remaining_times_and_active_color() -> None:
    user_data = register_user()
    clock = create_casual_clock(user_data)
    start_clock(user_data, clock["id"])

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}/events",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    start_event = response.json()["items"][1]
    assert start_event["white_remaining_ms"] == 300_000
    assert start_event["black_remaining_ms"] == 300_000
    assert start_event["active_color"] == "white"


def test_admin_can_create_pairing_linked_clock_session() -> None:
    admin, _, _, _, pairing = create_pairing_fixture()

    clock = create_official_clock(admin, pairing)

    assert clock["pairing_id"] == pairing["id"]
    assert clock["white_user_id"] == pairing["white_user"]["id"]
    assert clock["black_user_id"] == pairing["black_user"]["id"]


def test_duplicate_active_session_for_same_pairing_is_rejected() -> None:
    admin, _, _, _, pairing = create_pairing_fixture()
    create_official_clock(admin, pairing)

    response = client.post(
        "/api/v1/clock/sessions",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={"pairing_id": pairing["id"], "base_seconds": 300},
    )

    assert response.status_code == 409


def test_pairing_players_can_view_official_session() -> None:
    admin, _, black, _, pairing = create_pairing_fixture()
    clock = create_official_clock(admin, pairing)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(black["tokens"]["access_token"]),
    )

    assert response.status_code == 200


def test_non_player_member_cannot_view_official_session() -> None:
    admin, _, _, _, pairing = create_pairing_fixture()
    other = register_user("clock-other")
    clock = create_official_clock(admin, pairing)

    response = client.get(
        f"/api/v1/clock/sessions/{clock['id']}",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_pairing_player_cannot_control_official_session() -> None:
    admin, white, _, _, pairing = create_pairing_fixture()
    clock = create_official_clock(admin, pairing)

    response = client.post(
        f"/api/v1/clock/sessions/{clock['id']}/start",
        headers=auth_headers(white["tokens"]["access_token"]),
        json={**snapshot_payload(), "active_color": "white"},
    )

    assert response.status_code == 403


def test_admin_can_list_clock_sessions() -> None:
    user_data = register_user()
    admin = register_admin()
    clock = create_casual_clock(user_data)

    response = client.get(
        "/api/v1/admin/clock/sessions",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert clock["id"] in {item["id"] for item in response.json()["items"]}


def test_member_cannot_access_admin_clock_list() -> None:
    member = register_user()

    response = client.get(
        "/api/v1/admin/clock/sessions",
        headers=auth_headers(member["tokens"]["access_token"]),
    )

    assert response.status_code == 403
