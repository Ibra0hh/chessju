import asyncio
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.games.models import Game
from app.main import app
from app.tournaments.models import TournamentRegistration

client = TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "round-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Round Test User",
    }


def register_user(prefix: str = "round-test") -> dict:
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
    data = register_user("round-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def tournament_payload(slug: str | None = None, max_players: int = 16) -> dict:
    suffix = unique_suffix()
    starts_at = utc_now() + timedelta(hours=2)
    payload = {
        "title": f"Round Flow Tournament {suffix}",
        "slug": slug or f"round-flow-{suffix}",
        "description": "Round flow test tournament.",
        "status": "draft",
        "format": "swiss",
        "max_players": max_players,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
        "registration_close_at": (starts_at - timedelta(minutes=15)).isoformat(),
        "location": "University of Jordan",
    }
    return payload


def create_open_tournament(admin_data: dict, max_players: int = 16) -> dict:
    response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json=tournament_payload(max_players=max_players),
    )
    assert response.status_code == 201, response.text
    tournament = response.json()
    publish = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert publish.status_code == 200, publish.text
    opened = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/open-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert opened.status_code == 200, opened.text
    return opened.json()


def register_member_for_tournament(member_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/tournaments/{tournament_id}/register",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_registered_members(count: int, tournament_id: str) -> list[dict]:
    members = [register_user("round-member") for _ in range(count)]
    for member in members:
        register_member_for_tournament(member, tournament_id)
    return members


def create_round(admin_data: dict, tournament_id: str, round_number: int | None = 1) -> dict:
    payload = {"title": "Round 1"}
    if round_number is not None:
        payload["round_number"] = round_number
    response = client.post(
        f"/api/v1/admin/tournaments/{tournament_id}/rounds",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish_round(admin_data: dict, round_id: str) -> dict:
    response = client.post(
        f"/api/v1/admin/rounds/{round_id}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_pairing(
    admin_data: dict,
    round_id: str,
    white_user_id: str | None,
    black_user_id: str | None,
    board_number: int = 1,
    result: str = "pending",
) -> dict:
    response = client.post(
        f"/api/v1/admin/rounds/{round_id}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": board_number,
            "white_user_id": white_user_id,
            "black_user_id": black_user_id,
            "result": result,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit_result(admin_data: dict, pairing_id: str, result: str) -> dict:
    response = client.post(
        f"/api/v1/admin/pairings/{pairing_id}/result",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"result": result},
    )
    assert response.status_code == 200, response.text
    return response.json()


def setup_round_with_members(member_count: int = 2) -> tuple[dict, dict, list[dict], dict]:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data)
    members = create_registered_members(member_count, tournament["id"])
    close_response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/close-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert close_response.status_code == 200, close_response.text
    round_record = create_round(admin_data, tournament["id"])
    return admin_data, tournament, members, round_record


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


async def game_count_for_pairing(pairing_id: str) -> int:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(Game).where(Game.pairing_id == uuid.UUID(pairing_id))
        )
        return count or 0


async def force_registration_status(user_id: str, tournament_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.user_id == uuid.UUID(user_id),
                TournamentRegistration.tournament_id == uuid.UUID(tournament_id),
            )
        )
        registration = result.scalar_one()
        registration.status = status
        await session.commit()


def test_admin_can_create_round() -> None:
    admin_data, tournament, _, _ = setup_round_with_members()
    round_record = create_round(admin_data, tournament["id"], round_number=2)

    assert round_record["round_number"] == 2
    assert round_record["status"] == "draft"


def test_member_cannot_create_round() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data)
    member = register_user()

    response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/rounds",
        headers=auth_headers(member["tokens"]["access_token"]),
        json={"round_number": 1},
    )

    assert response.status_code == 403


def test_public_cannot_see_draft_round() -> None:
    admin_data, tournament, _, round_record = setup_round_with_members()

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/rounds")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert round_record["id"] not in ids


def test_public_can_see_published_round() -> None:
    admin_data, tournament, _, round_record = setup_round_with_members()
    publish_round(admin_data, round_record["id"])

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/rounds")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert round_record["id"] in ids


def test_admin_can_publish_start_complete_cancel_round() -> None:
    admin_data, _, _, round_record = setup_round_with_members()

    published = publish_round(admin_data, round_record["id"])
    started = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/start",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    completed = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/complete",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    cancelled = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/cancel",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert published["status"] == "published"
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_duplicate_round_number_rejected() -> None:
    admin_data, tournament, _, _ = setup_round_with_members()

    response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/rounds",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"round_number": 1},
    )

    assert response.status_code == 409


def test_admin_can_create_manual_pairing() -> None:
    admin_data, _, members, round_record = setup_round_with_members()

    pairing = create_pairing(
        admin_data,
        round_record["id"],
        members[0]["user"]["id"],
        members[1]["user"]["id"],
    )

    assert pairing["board_number"] == 1
    assert pairing["white_user"]["id"] == members[0]["user"]["id"]


def test_member_cannot_create_pairing() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    member = members[0]

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(member["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": members[0]["user"]["id"],
            "black_user_id": members[1]["user"]["id"],
        },
    )

    assert response.status_code == 403


def test_pairing_requires_approved_registered_players() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    outsider = register_user("outsider")

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": members[0]["user"]["id"],
            "black_user_id": outsider["user"]["id"],
        },
    )

    assert response.status_code == 400


def test_player_cannot_be_paired_twice_in_same_round() -> None:
    admin_data, _, members, round_record = setup_round_with_members(3)
    create_pairing(
        admin_data,
        round_record["id"],
        members[0]["user"]["id"],
        members[1]["user"]["id"],
    )

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": 2,
            "white_user_id": members[0]["user"]["id"],
            "black_user_id": members[2]["user"]["id"],
        },
    )

    assert response.status_code == 409


def test_white_user_id_cannot_equal_black_user_id() -> None:
    admin_data, _, members, round_record = setup_round_with_members()

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": members[0]["user"]["id"],
            "black_user_id": members[0]["user"]["id"],
        },
    )

    assert response.status_code == 400


def test_duplicate_board_number_rejected() -> None:
    admin_data, _, members, round_record = setup_round_with_members(4)
    create_pairing(
        admin_data,
        round_record["id"],
        members[0]["user"]["id"],
        members[1]["user"]["id"],
    )

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": members[2]["user"]["id"],
            "black_user_id": members[3]["user"]["id"],
        },
    )

    assert response.status_code == 409


def test_bye_pairing_works_with_exactly_one_player() -> None:
    admin_data, _, members, round_record = setup_round_with_members()

    pairing = create_pairing(
        admin_data,
        round_record["id"],
        members[0]["user"]["id"],
        None,
        result="bye",
    )

    assert pairing["result"] == "bye"
    assert pairing["status"] == "completed"


def test_invalid_bye_pairing_rejected() -> None:
    admin_data, _, _, round_record = setup_round_with_members()

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"board_number": 1, "result": "bye"},
    )

    assert response.status_code == 400


def test_bulk_pairing_creates_multiple_pairings_transactionally() -> None:
    admin_data, _, members, round_record = setup_round_with_members(4)

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings/bulk",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "pairings": [
                {
                    "board_number": 1,
                    "white_user_id": members[0]["user"]["id"],
                    "black_user_id": members[1]["user"]["id"],
                },
                {
                    "board_number": 2,
                    "white_user_id": members[2]["user"]["id"],
                    "black_user_id": members[3]["user"]["id"],
                },
            ]
        },
    )

    assert response.status_code == 201
    assert response.json()["total"] == 2


def test_bulk_pairing_rejects_duplicate_players() -> None:
    admin_data, _, members, round_record = setup_round_with_members(3)

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings/bulk",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "pairings": [
                {
                    "board_number": 1,
                    "white_user_id": members[0]["user"]["id"],
                    "black_user_id": members[1]["user"]["id"],
                },
                {
                    "board_number": 2,
                    "white_user_id": members[0]["user"]["id"],
                    "black_user_id": members[2]["user"]["id"],
                },
            ]
        },
    )

    assert response.status_code == 409


def test_bulk_pairing_rejects_duplicate_boards() -> None:
    admin_data, _, members, round_record = setup_round_with_members(4)

    response = client.post(
        f"/api/v1/admin/rounds/{round_record['id']}/pairings/bulk",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "pairings": [
                {
                    "board_number": 1,
                    "white_user_id": members[0]["user"]["id"],
                    "black_user_id": members[1]["user"]["id"],
                },
                {
                    "board_number": 1,
                    "white_user_id": members[2]["user"]["id"],
                    "black_user_id": members[3]["user"]["id"],
                },
            ]
        },
    )

    assert response.status_code == 409


def test_admin_can_submit_white_win_black_win_and_draw() -> None:
    admin_data, _, members, round_record = setup_round_with_members(6)
    white_win = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"], 1
    )
    black_win = create_pairing(
        admin_data, round_record["id"], members[2]["user"]["id"], members[3]["user"]["id"], 2
    )
    draw = create_pairing(
        admin_data, round_record["id"], members[4]["user"]["id"], members[5]["user"]["id"], 3
    )

    assert submit_result(admin_data, white_win["id"], "white_win")["result"] == "white_win"
    assert submit_result(admin_data, black_win["id"], "black_win")["result"] == "black_win"
    assert submit_result(admin_data, draw["id"], "draw")["result"] == "draw"


def test_admin_can_submit_bye_result() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(admin_data, round_record["id"], members[0]["user"]["id"], None)

    response = submit_result(admin_data, pairing["id"], "bye")

    assert response["result"] == "bye"
    assert response["status"] == "completed"


def test_member_cannot_submit_result() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )

    response = client.post(
        f"/api/v1/admin/pairings/{pairing['id']}/result",
        headers=auth_headers(members[0]["tokens"]["access_token"]),
        json={"result": "white_win"},
    )

    assert response.status_code == 403


def test_result_submission_creates_linked_game_record_and_update_reuses_it() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )
    submit_result(admin_data, pairing["id"], "white_win")
    first_count = asyncio.run(game_count_for_pairing(pairing["id"]))
    submit_result(admin_data, pairing["id"], "draw")
    second_count = asyncio.run(game_count_for_pairing(pairing["id"]))

    assert first_count == 1
    assert second_count == 1


def test_cannot_submit_result_for_cancelled_pairing() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )
    cancel_response = client.delete(
        f"/api/v1/admin/pairings/{pairing['id']}",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    response = client.post(
        f"/api/v1/admin/pairings/{pairing['id']}/result",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"result": "white_win"},
    )

    assert cancel_response.status_code == 200
    assert response.status_code == 400


def test_result_mutation_creates_audit_log() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )
    submit_result(admin_data, pairing["id"], "white_win")
    log = latest_audit_log("pairing.result_submitted", pairing["id"], admin_data)

    assert log["after"]["result"] == "white_win"


def test_public_round_detail_and_pairings_endpoints_work() -> None:
    admin_data, tournament, members, round_record = setup_round_with_members()
    publish_round(admin_data, round_record["id"])
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )

    rounds = client.get(f"/api/v1/tournaments/{tournament['slug']}/rounds")
    detail = client.get(f"/api/v1/tournaments/{tournament['slug']}/rounds/1")
    pairings = client.get(f"/api/v1/tournaments/{tournament['slug']}/pairings?round_number=1")

    assert rounds.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["pairings"][0]["id"] == pairing["id"]
    assert pairings.status_code == 200
    assert pairings.json()["items"][0]["id"] == pairing["id"]


def test_user_me_pairings_returns_own_pairings() -> None:
    admin_data, _, members, round_record = setup_round_with_members()
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )

    response = client.get(
        "/api/v1/users/me/pairings",
        headers=auth_headers(members[0]["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert pairing["id"] in ids


def test_standings_include_approved_registered_players_with_zero_points() -> None:
    admin_data, tournament, members, _ = setup_round_with_members()

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/standings")

    assert response.status_code == 200
    ids = {item["user_id"] for item in response.json()["items"]}
    assert {member["user"]["id"] for member in members}.issubset(ids)
    assert all(item["points"] == 0 for item in response.json()["items"])


def test_standings_compute_win_loss_draw_bye_and_sort_by_points() -> None:
    admin_data, tournament, members, round_record = setup_round_with_members(5)
    p1, p2, p3, p4, p5 = members
    submit_result(
        admin_data,
        create_pairing(admin_data, round_record["id"], p1["user"]["id"], p2["user"]["id"], 1)["id"],
        "white_win",
    )
    submit_result(
        admin_data,
        create_pairing(admin_data, round_record["id"], p3["user"]["id"], p4["user"]["id"], 2)["id"],
        "draw",
    )
    submit_result(
        admin_data,
        create_pairing(admin_data, round_record["id"], p5["user"]["id"], None, 3)["id"],
        "bye",
    )

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/standings")

    assert response.status_code == 200
    rows = {item["user_id"]: item for item in response.json()["items"]}
    assert rows[p1["user"]["id"]]["wins"] == 1
    assert rows[p2["user"]["id"]]["losses"] == 1
    assert rows[p3["user"]["id"]]["draws"] == 1
    assert rows[p4["user"]["id"]]["points"] == 0.5
    assert rows[p5["user"]["id"]]["byes"] == 1
    points = [item["points"] for item in response.json()["items"]]
    assert points == sorted(points, reverse=True)


def test_pending_pairings_do_not_affect_standings() -> None:
    admin_data, tournament, members, round_record = setup_round_with_members()
    create_pairing(
        admin_data,
        round_record["id"],
        members[0]["user"]["id"],
        members[1]["user"]["id"],
    )

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/standings")

    assert response.status_code == 200
    assert all(item["points"] == 0 for item in response.json()["items"])


def test_cancelled_rejected_waitlisted_registrations_excluded_from_standings() -> None:
    admin_data = register_admin()
    tournament = create_open_tournament(admin_data, max_players=2)
    members = create_registered_members(4, tournament["id"])
    asyncio.run(force_registration_status(members[1]["user"]["id"], tournament["id"], "cancelled"))
    asyncio.run(force_registration_status(members[2]["user"]["id"], tournament["id"], "rejected"))
    asyncio.run(force_registration_status(members[3]["user"]["id"], tournament["id"], "waitlisted"))

    response = client.get(f"/api/v1/tournaments/{tournament['slug']}/standings")

    assert response.status_code == 200
    ids = {item["user_id"] for item in response.json()["items"]}
    assert members[0]["user"]["id"] in ids
    assert members[1]["user"]["id"] not in ids
    assert members[2]["user"]["id"] not in ids
    assert members[3]["user"]["id"] not in ids
