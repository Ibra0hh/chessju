import asyncio
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.leaderboard.models import LeaderboardSnapshot
from app.main import app
from app.tournaments.models import TournamentRegistration

client = TestClient(app)
_future_day_counter = 0


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def unique_future_start() -> datetime:
    global _future_day_counter
    _future_day_counter += 1
    random_offset = int(uuid.uuid4().hex[:8], 16) % 500_000
    return utc_now() + timedelta(days=1000 + random_offset + _future_day_counter)


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(
    prefix: str = "leaderboard-test", username: str | None = None
) -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": username or f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Leaderboard Test User",
    }


def register_user(prefix: str = "leaderboard-test", username: str | None = None) -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload(prefix, username))
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
    data = register_user("leaderboard-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def create_season(
    admin_data: dict,
    starts_at: str | None = None,
    ends_at: str | None = None,
    active: bool = False,
) -> dict:
    start = unique_future_start()
    end = start + timedelta(days=1)
    response = client.post(
        "/api/v1/admin/leaderboard/seasons",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "name": f"Season {unique_suffix()}",
            "starts_at": starts_at or start.isoformat(),
            "ends_at": ends_at or end.isoformat(),
            "active": active,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_tournament_at(admin_data: dict, starts_at) -> dict:
    suffix = unique_suffix()
    response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "title": f"Leaderboard Tournament {suffix}",
            "slug": f"leaderboard-{suffix}",
            "description": "Leaderboard test tournament.",
            "status": "draft",
            "format": "swiss",
            "max_players": 32,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
            "registration_close_at": (starts_at - timedelta(hours=1)).isoformat(),
            "location": "University of Jordan",
        },
    )
    assert response.status_code == 201, response.text
    tournament = response.json()
    publish = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert publish.status_code == 200, publish.text
    open_registration = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/open-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert open_registration.status_code == 200, open_registration.text
    return open_registration.json()


def register_member_for_tournament(member_data: dict, tournament_id: str) -> dict:
    response = client.post(
        f"/api/v1/tournaments/{tournament_id}/register",
        headers=auth_headers(member_data["tokens"]["access_token"]),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_round(admin_data: dict, tournament_id: str, round_number: int = 1) -> dict:
    response = client.post(
        f"/api/v1/admin/tournaments/{tournament_id}/rounds",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"round_number": round_number, "title": f"Round {round_number}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_pairing(
    admin_data: dict,
    round_id: str,
    white_user_id: str | None,
    black_user_id: str | None,
    board_number: int = 1,
) -> dict:
    response = client.post(
        f"/api/v1/admin/rounds/{round_id}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": board_number,
            "white_user_id": white_user_id,
            "black_user_id": black_user_id,
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


def create_season_tournament(
    admin_data: dict,
    member_count: int,
    active: bool = False,
) -> tuple[dict, dict, list[dict], dict]:
    starts_at = unique_future_start()
    season = create_season(
        admin_data,
        starts_at=(starts_at - timedelta(hours=2)).isoformat(),
        ends_at=(starts_at + timedelta(hours=4)).isoformat(),
        active=active,
    )
    tournament = create_tournament_at(admin_data, starts_at)
    members = [register_user("leaderboard-member") for _ in range(member_count)]
    for member in members:
        register_member_for_tournament(member, tournament["id"])
    round_record = create_round(admin_data, tournament["id"])
    return season, tournament, members, round_record


def recompute(admin_data: dict, season_id: str | None = None) -> dict:
    response = client.post(
        "/api/v1/admin/leaderboard/recompute",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"season_id": season_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def rows_by_user(leaderboard: dict) -> dict[str, dict]:
    return {row["user_id"]: row for row in leaderboard["rows"]}


async def snapshot_count(season_id: str | None) -> int:
    async with AsyncSessionLocal() as session:
        statement = select(func.count()).select_from(LeaderboardSnapshot)
        if season_id is None:
            statement = statement.where(LeaderboardSnapshot.season_id.is_(None))
        else:
            statement = statement.where(LeaderboardSnapshot.season_id == uuid.UUID(season_id))
        count = await session.scalar(statement)
        return count or 0


async def force_registration_status(user_id: str, tournament_id: str, next_status: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.user_id == uuid.UUID(user_id),
                TournamentRegistration.tournament_id == uuid.UUID(tournament_id),
            )
        )
        registration = result.scalar_one()
        registration.status = next_status
        await session.commit()


def latest_audit_log(action: str, entity_id: str | None, admin_data: dict) -> dict:
    response = client.get(
        f"/api/v1/admin/audit-logs?action={action}&limit=50",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        if item["entity_id"] == entity_id:
            return item
    raise AssertionError(f"Audit log not found for {action} {entity_id}")


def paged_ids(path: str, headers: dict[str, str] | None = None) -> set[str]:
    ids: set[str] = set()
    offset = 0
    while True:
        separator = "&" if "?" in path else "?"
        response = client.get(f"{path}{separator}limit=100&offset={offset}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        ids.update(item["id"] for item in body["items"])
        offset += len(body["items"])
        if offset >= body["total"] or not body["items"]:
            break
    return ids


def test_admin_can_create_season() -> None:
    admin_data = register_admin()
    season = create_season(admin_data)

    assert season["name"].startswith("Season")
    assert season["active"] is False


def test_member_cannot_create_season() -> None:
    member_data = register_user()
    start = utc_now() + timedelta(days=10)

    response = client.post(
        "/api/v1/admin/leaderboard/seasons",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json={
            "name": "Unauthorized Season",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 403


def test_admin_can_activate_season_and_deactivates_others() -> None:
    admin_data = register_admin()
    first = create_season(admin_data, active=True)
    second = create_season(admin_data)

    response = client.post(
        f"/api/v1/admin/leaderboard/seasons/{second['id']}/activate",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    season_ids = paged_ids(
        "/api/v1/admin/leaderboard/seasons",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["active"] is True
    assert first["id"] in season_ids
    assert second["id"] in season_ids
    assert client.get(
        f"/api/v1/leaderboard/seasons/{first['id']}",
    ).json()["season"]["active"] is False
    assert client.get(
        f"/api/v1/leaderboard/seasons/{second['id']}",
    ).json()["season"]["active"] is True


def test_invalid_season_date_range_is_rejected() -> None:
    admin_data = register_admin()
    start = utc_now() + timedelta(days=30)

    response = client.post(
        "/api/v1/admin/leaderboard/seasons",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "name": "Invalid Season",
            "starts_at": start.isoformat(),
            "ends_at": (start - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 422


def test_admin_can_recompute_all_time_leaderboard() -> None:
    admin_data = register_admin()
    _, _, members, round_record = create_season_tournament(admin_data, 2)
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )
    submit_result(admin_data, pairing["id"], "white_win")

    leaderboard = recompute(admin_data)

    assert leaderboard["season"] is None
    assert leaderboard["total"] >= 2


def test_member_cannot_recompute_leaderboard() -> None:
    member_data = register_user()

    response = client.post(
        "/api/v1/admin/leaderboard/recompute",
        headers=auth_headers(member_data["tokens"]["access_token"]),
        json={"season_id": None},
    )

    assert response.status_code == 403


def test_recompute_creates_and_replaces_leaderboard_snapshots() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    pairing = create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )
    submit_result(admin_data, pairing["id"], "white_win")

    first = recompute(admin_data, season["id"])
    first_count = asyncio.run(snapshot_count(season["id"]))
    second = recompute(admin_data, season["id"])
    second_count = asyncio.run(snapshot_count(season["id"]))

    assert first["total"] == 2
    assert second["total"] == 2
    assert first_count == 2
    assert second_count == 2


def test_empty_data_recompute_returns_empty_rows_safely() -> None:
    admin_data = register_admin()
    start = utc_now() - timedelta(days=9000)
    season = create_season(
        admin_data,
        starts_at=start.isoformat(),
        ends_at=(start + timedelta(days=1)).isoformat(),
    )

    leaderboard = recompute(admin_data, season["id"])

    assert leaderboard["rows"] == []
    assert leaderboard["total"] == 0


def test_white_win_scores_white_one_and_black_zero() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "white_win",
    )

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert rows[members[0]["user"]["id"]]["points"] == 1.0
    assert rows[members[0]["user"]["id"]]["wins"] == 1
    assert rows[members[1]["user"]["id"]]["points"] == 0.0
    assert rows[members[1]["user"]["id"]]["losses"] == 1


def test_black_win_scores_black_one_and_white_zero() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "black_win",
    )

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert rows[members[1]["user"]["id"]]["points"] == 1.0
    assert rows[members[1]["user"]["id"]]["wins"] == 1
    assert rows[members[0]["user"]["id"]]["points"] == 0.0


def test_draw_scores_both_half_point() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "draw",
    )

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert rows[members[0]["user"]["id"]]["points"] == 0.5
    assert rows[members[1]["user"]["id"]]["points"] == 0.5
    assert rows[members[0]["user"]["id"]]["draws"] == 1
    assert rows[members[1]["user"]["id"]]["draws"] == 1


def test_bye_scores_player_one_point() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 1)
    submit_result(
        admin_data,
        create_pairing(admin_data, round_record["id"], members[0]["user"]["id"], None)["id"],
        "bye",
    )

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert rows[members[0]["user"]["id"]]["points"] == 1.0
    assert rows[members[0]["user"]["id"]]["byes"] == 1


def test_pending_pairings_are_ignored() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    create_pairing(
        admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
    )

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert all(row["points"] == 0 for row in rows.values())
    assert all(row["games_played"] == 0 for row in rows.values())


def test_waitlisted_cancelled_and_rejected_users_are_excluded() -> None:
    admin_data = register_admin()
    season, tournament, members, _ = create_season_tournament(admin_data, 4)
    asyncio.run(force_registration_status(members[1]["user"]["id"], tournament["id"], "waitlisted"))
    asyncio.run(force_registration_status(members[2]["user"]["id"], tournament["id"], "cancelled"))
    asyncio.run(force_registration_status(members[3]["user"]["id"], tournament["id"], "rejected"))

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert members[0]["user"]["id"] in rows
    assert members[1]["user"]["id"] not in rows
    assert members[2]["user"]["id"] not in rows
    assert members[3]["user"]["id"] not in rows


def test_approved_players_with_zero_games_are_included() -> None:
    admin_data = register_admin()
    season, _, members, _ = create_season_tournament(admin_data, 3)

    rows = rows_by_user(recompute(admin_data, season["id"]))

    assert {member["user"]["id"] for member in members}.issubset(rows)
    assert all(rows[member["user"]["id"]]["points"] == 0 for member in members)


def test_rows_sort_by_points_descending() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 3)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"], 1
        )["id"],
        "white_win",
    )

    leaderboard = recompute(admin_data, season["id"])

    points = [row["points"] for row in leaderboard["rows"]]
    assert points == sorted(points, reverse=True)


def test_tie_sorts_by_wins_descending() -> None:
    admin_data = register_admin()
    season, tournament, members, round_one = create_season_tournament(admin_data, 5)
    p1, p2, p3, p4, p5 = members
    submit_result(
        admin_data,
        create_pairing(admin_data, round_one["id"], p1["user"]["id"], p5["user"]["id"], 1)["id"],
        "white_win",
    )
    submit_result(
        admin_data,
        create_pairing(admin_data, round_one["id"], p2["user"]["id"], p3["user"]["id"], 2)["id"],
        "draw",
    )
    round_two = create_round(admin_data, tournament["id"], round_number=2)
    submit_result(
        admin_data,
        create_pairing(admin_data, round_two["id"], p2["user"]["id"], p4["user"]["id"], 1)["id"],
        "draw",
    )

    leaderboard = recompute(admin_data, season["id"])
    ordered_ids = [row["user_id"] for row in leaderboard["rows"]]

    assert ordered_ids.index(p1["user"]["id"]) < ordered_ids.index(p2["user"]["id"])


def test_tie_eventually_sorts_by_username_ascending() -> None:
    admin_data = register_admin()
    starts_at = unique_future_start()
    season = create_season(
        admin_data,
        starts_at=(starts_at - timedelta(hours=2)).isoformat(),
        ends_at=(starts_at + timedelta(hours=4)).isoformat(),
    )
    tournament = create_tournament_at(admin_data, starts_at)
    second = register_user("leaderboard-member", username=f"zz_{unique_suffix()}")
    first = register_user("leaderboard-member", username=f"aa_{unique_suffix()}")
    register_member_for_tournament(second, tournament["id"])
    register_member_for_tournament(first, tournament["id"])

    leaderboard = recompute(admin_data, season["id"])

    usernames = [row["username"] for row in leaderboard["rows"]]
    assert usernames == sorted(usernames)


def test_public_leaderboard_returns_rows_for_active_season() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2, active=True)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "white_win",
    )
    recompute(admin_data, season["id"])

    response = client.get("/api/v1/leaderboard")

    assert response.status_code == 200
    assert response.json()["season"]["id"] == season["id"]
    assert response.json()["total"] == 2


def test_public_leaderboard_seasons_returns_seasons() -> None:
    admin_data = register_admin()
    season = create_season(admin_data)

    ids = paged_ids("/api/v1/leaderboard/seasons")
    assert season["id"] in ids


def test_public_leaderboard_for_specific_season_returns_rows() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "white_win",
    )
    recompute(admin_data, season["id"])

    response = client.get(f"/api/v1/leaderboard/seasons/{season['id']}")

    assert response.status_code == 200
    assert response.json()["season"]["id"] == season["id"]
    assert response.json()["total"] == 2


def test_home_includes_leaderboard_preview_top_rows() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2, active=True)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "white_win",
    )
    recompute(admin_data, season["id"])

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["leaderboard_preview"][0]["user_id"] == members[0]["user"]["id"]


def test_home_returns_empty_leaderboard_preview_if_no_snapshot_exists() -> None:
    admin_data = register_admin()
    create_season(admin_data, active=True)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["leaderboard_preview"] == []


def test_admin_leaderboard_endpoint_works() -> None:
    admin_data = register_admin()
    season, _, members, round_record = create_season_tournament(admin_data, 2, active=True)
    submit_result(
        admin_data,
        create_pairing(
            admin_data, round_record["id"], members[0]["user"]["id"], members[1]["user"]["id"]
        )["id"],
        "white_win",
    )
    recompute(admin_data, season["id"])

    response = client.get(
        "/api/v1/admin/leaderboard",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["season"]["id"] == season["id"]
    assert response.json()["total"] == 2


def test_leaderboard_recompute_writes_audit_log() -> None:
    admin_data = register_admin()
    season, _, _, _ = create_season_tournament(admin_data, 1)
    recompute(admin_data, season["id"])

    log = latest_audit_log("leaderboard.recomputed", season["id"], admin_data)

    assert log["after"]["season_id"] == season["id"]


def test_season_activation_writes_audit_log() -> None:
    admin_data = register_admin()
    season = create_season(admin_data)

    response = client.post(
        f"/api/v1/admin/leaderboard/seasons/{season['id']}/activate",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    log = latest_audit_log("season.activated", season["id"], admin_data)

    assert response.status_code == 200
    assert log["after"]["active"] is True
