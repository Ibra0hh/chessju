import asyncio
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import Role, UserRole
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.games.models import Game, GameMove
from app.main import app
from app.pgn.models import PgnImport

client = TestClient(app)

VALID_PGN = """[Event "ChessJU Test"]
[Site "Amman"]
[Date "2026.05.19"]
[Round "1"]
[White "Ibrahim"]
[Black "Dana"]
[Result "1-0"]
[ECO "C20"]
[Opening "King's Pawn Game"]
[TimeControl "600+5"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

CHECKMATE_PGN = """[Event "Mate Test"]
[Site "Amman"]
[Date "2026.05.19"]
[Round "1"]
[White "Ibrahim"]
[Black "Dana"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "pgn-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "PGN Test User",
    }


def register_user(prefix: str = "pgn-test") -> dict:
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
    data = register_user("pgn-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def paste_pgn(user_data: dict, pgn_text: str = VALID_PGN) -> dict:
    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": pgn_text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_pgn(
    user_data: dict,
    filename: str = "game.pgn",
    content_type: str = "application/x-chess-pgn",
) -> dict:
    response = client.post(
        "/api/v1/games/pgn/upload",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        files={"file": (filename, VALID_PGN.encode("utf-8"), content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def game_move_count(game_id: str) -> int:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(GameMove).where(GameMove.game_id == uuid.UUID(game_id))
        )
        return count or 0


async def import_count_for_game(game_id: str) -> int:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(PgnImport)
            .where(PgnImport.game_id == uuid.UUID(game_id))
        )
        return count or 0


async def game_id_for_pairing(pairing_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Game.id).where(Game.pairing_id == uuid.UUID(pairing_id))
        )
        return str(result.scalar_one())


def create_tournament_game() -> tuple[dict, dict, dict, str]:
    admin_data = register_admin()
    white = register_user("pgn-white")
    black = register_user("pgn-black")
    starts_at = utc_now() + timedelta(days=10)
    tournament_response = client.post(
        "/api/v1/admin/tournaments",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "title": f"PGN Compatibility {unique_suffix()}",
            "description": "Tournament game compatibility test.",
            "status": "draft",
            "format": "swiss",
            "max_players": 8,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
            "registration_close_at": (starts_at - timedelta(hours=1)).isoformat(),
            "location": "University of Jordan",
        },
    )
    assert tournament_response.status_code == 201, tournament_response.text
    tournament = tournament_response.json()
    client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/publish",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/open-registration",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
    )
    for member in (white, black):
        response = client.post(
            f"/api/v1/tournaments/{tournament['id']}/register",
            headers=auth_headers(member["tokens"]["access_token"]),
        )
        assert response.status_code == 201, response.text
    round_response = client.post(
        f"/api/v1/admin/tournaments/{tournament['id']}/rounds",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"round_number": 1, "title": "Round 1"},
    )
    assert round_response.status_code == 201, round_response.text
    pairing_response = client.post(
        f"/api/v1/admin/rounds/{round_response.json()['id']}/pairings",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={
            "board_number": 1,
            "white_user_id": white["user"]["id"],
            "black_user_id": black["user"]["id"],
        },
    )
    assert pairing_response.status_code == 201, pairing_response.text
    result_response = client.post(
        f"/api/v1/admin/pairings/{pairing_response.json()['id']}/result",
        headers=auth_headers(admin_data["tokens"]["access_token"]),
        json={"result": "white_win"},
    )
    assert result_response.status_code == 200, result_response.text
    game_id = asyncio.run(game_id_for_pairing(pairing_response.json()["id"]))
    return admin_data, white, black, game_id


def test_authenticated_user_can_paste_valid_pgn() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    assert game["source"] == "pgn_upload"
    assert game["white_name"] == "Ibrahim"
    assert game["black_name"] == "Dana"
    assert game["moves"]


def test_unauthenticated_user_cannot_paste_pgn() -> None:
    response = client.post("/api/v1/games/pgn/paste", json={"pgn_text": VALID_PGN})

    assert response.status_code == 401


def test_empty_pgn_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": "   "},
    )

    assert response.status_code == 400


def test_invalid_pgn_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": "not a valid game"},
    )

    assert response.status_code == 400


def test_oversized_pgn_paste_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": VALID_PGN + (" " * (210 * 1024))},
    )

    assert response.status_code == 413


def test_valid_pgn_creates_game_and_moves() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    assert game["id"]
    assert asyncio.run(game_move_count(game["id"])) == len(game["moves"])
    assert len(game["moves"]) == 6


def test_metadata_extracted_correctly() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    assert game["metadata"]["Event"] == "ChessJU Test"
    assert game["metadata"]["ECO"] == "C20"
    assert game["metadata"]["Opening"] == "King's Pawn Game"
    assert game["time_control"] == "600+5"
    assert game["played_at"].startswith("2026-05-19")


def test_san_uci_and_fen_values_are_returned() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    first_move = game["moves"][0]

    assert first_move["san"] == "e4"
    assert first_move["uci"] == "e2e4"
    assert first_move["fen_before"] == game["initial_fen"]
    assert " b " in first_move["fen_after"]
    assert game["final_fen"] == game["moves"][-1]["fen_after"]


def test_checkmate_flag_is_returned() -> None:
    user_data = register_user()
    game = paste_pgn(user_data, CHECKMATE_PGN)

    assert game["moves"][-1]["san"].endswith("#")
    assert game["moves"][-1]["is_check"] is True
    assert game["moves"][-1]["is_checkmate"] is True


def test_authenticated_user_can_upload_pgn_file() -> None:
    user_data = register_user()
    game = upload_pgn(user_data)

    assert game["source"] == "pgn_upload"
    assert game["moves"][0]["uci"] == "e2e4"


def test_invalid_extension_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/upload",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        files={"file": ("game.exe", VALID_PGN.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400


def test_invalid_mime_or_content_rejected() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/upload",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        files={"file": ("game.pgn", b"not a valid game", "text/plain")},
    )

    assert response.status_code == 400


def test_file_metadata_does_not_expose_internal_path() -> None:
    user_data = register_user()

    response = client.post(
        "/api/v1/games/pgn/upload",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        files={"file": ("folder/game.pgn", VALID_PGN.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201, response.text
    body_text = response.text.lower()
    assert "storage_path" not in body_text
    assert "c:\\" not in body_text
    assert "/data/storage" not in body_text


def test_uploaded_file_creates_pgn_import_record() -> None:
    user_data = register_user()
    game = upload_pgn(user_data)

    response = client.get(
        "/api/v1/pgn-imports",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    imports = [item for item in response.json()["items"] if item["game_id"] == game["id"]]
    assert imports
    assert imports[0]["source"] == "file_upload"
    assert imports[0]["file_id"] is not None
    assert asyncio.run(import_count_for_game(game["id"])) == 1


def test_user_can_list_own_uploaded_games() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    response = client.get(
        "/api/v1/games?source=pgn_upload",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert game["id"] in ids


def test_user_cannot_view_another_users_private_uploaded_pgn_game() -> None:
    owner = register_user("pgn-owner")
    other = register_user("pgn-other")
    game = paste_pgn(owner)

    response = client.get(
        f"/api/v1/games/{game['id']}",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_admin_can_view_all_games() -> None:
    owner = register_user("pgn-owner")
    admin = register_admin()
    game = paste_pgn(owner)

    response = client.get(
        f"/api/v1/games/{game['id']}",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == game["id"]


def test_user_can_view_own_game_detail_with_moves() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    response = client.get(
        f"/api/v1/games/{game['id']}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["moves"][0]["san"] == "e4"


def test_game_moves_endpoint_returns_ordered_moves() -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    response = client.get(
        f"/api/v1/games/{game['id']}/moves",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    ply_numbers = [move["ply_number"] for move in response.json()]
    assert ply_numbers == sorted(ply_numbers)


def test_pgn_imports_returns_only_current_users_imports() -> None:
    first = register_user("pgn-first")
    second = register_user("pgn-second")
    first_game = paste_pgn(first)
    paste_pgn(second)

    response = client.get(
        "/api/v1/pgn-imports",
        headers=auth_headers(first["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    game_ids = {item["game_id"] for item in response.json()["items"]}
    assert first_game["id"] in game_ids
    assert len(game_ids) == 1


def test_admin_pgn_imports_and_games_endpoints_work() -> None:
    owner = register_user("pgn-owner")
    admin = register_admin()
    game = paste_pgn(owner)

    imports_response = client.get(
        "/api/v1/admin/pgn-imports",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    games_response = client.get(
        "/api/v1/admin/games?source=pgn_upload",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert imports_response.status_code == 200
    assert games_response.status_code == 200
    assert game["id"] in {item["game_id"] for item in imports_response.json()["items"]}
    assert game["id"] in {item["id"] for item in games_response.json()["items"]}


def test_user_can_view_tournament_game_where_they_are_a_player() -> None:
    _, white, _, game_id = create_tournament_game()

    response = client.get(
        f"/api/v1/games/{game_id}",
        headers=auth_headers(white["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["source"] == "tournament"
    assert response.json()["moves"] == []


def test_existing_tournament_games_still_appear_in_user_game_library() -> None:
    _, white, _, game_id = create_tournament_game()

    response = client.get(
        "/api/v1/games?source=tournament",
        headers=auth_headers(white["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert game_id in {item["id"] for item in response.json()["items"]}
