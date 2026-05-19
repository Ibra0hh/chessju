import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import Role, UserRole
from app.chesscom.models import ChessComImportedGame, ChessComSyncJob
from app.chesscom.tasks import run_chesscom_sync_job_async
from app.database import AsyncSessionLocal
from app.games.models import Game, GameMove
from app.main import app
from app.pgn.models import PgnImport

client = TestClient(app)

VALID_PGN = """[Event "Chess.com Import Test"]
[Site "Chess.com"]
[Date "2026.05.19"]
[Round "-"]
[White "Ibra0hh"]
[Black "Opponent"]
[Result "1-0"]
[ECO "C20"]
[Opening "King's Pawn Game"]
[TimeControl "600"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


class FakeChessComClient:
    def __init__(
        self,
        profile_username: str | None = None,
        archives: list[str] | None = None,
        games_by_archive: dict[str, list[dict[str, Any]]] | None = None,
        fail_archives: bool = False,
    ) -> None:
        self.profile_username = profile_username
        self.archives = archives or ["https://api.chess.com/pub/player/ibra0hh/games/2026/05"]
        self.games_by_archive = games_by_archive or {self.archives[0]: [mock_chesscom_game()]}
        self.fail_archives = fail_archives

    async def fetch_profile(self, username: str) -> dict[str, Any]:
        canonical = self.profile_username or username
        return {
            "username": canonical,
            "url": f"https://www.chess.com/member/{canonical}",
            "title": "NM",
            "country": "https://api.chess.com/pub/country/JO",
            "avatar": "https://images.chesscomfiles.com/uploads/v1/user/1.abc.jpeg",
            "joined": 1_700_000_000,
            "last_online": 1_780_000_000,
        }

    async def fetch_archives(self, username: str) -> list[str]:
        _ = username
        if self.fail_archives:
            raise RuntimeError("public api unavailable")
        return self.archives

    async def fetch_archive_games(self, archive_url: str) -> list[dict[str, Any]]:
        return self.games_by_archive.get(archive_url, [])


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def unique_chesscom_username(prefix: str = "Ibra0hh") -> str:
    return f"{prefix}_{unique_suffix()}"


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "chesscom-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Chess.com Test User",
    }


def register_user(prefix: str = "chesscom-test") -> dict:
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
    data = register_user("chesscom-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def mock_chesscom_game(url: str | None = None, pgn: str = VALID_PGN) -> dict[str, Any]:
    game_url = url or f"https://www.chess.com/game/live/{unique_suffix()}"
    return {
        "url": game_url,
        "uuid": unique_suffix(),
        "pgn": pgn,
        "end_time": int(datetime(2026, 5, 19, tzinfo=UTC).timestamp()),
        "rated": True,
        "time_class": "rapid",
        "time_control": "600",
        "white": {"username": "Ibra0hh", "result": "win", "uuid": unique_suffix()},
        "black": {"username": "Opponent", "result": "checkmated", "uuid": unique_suffix()},
    }


def disable_chesscom_queue(monkeypatch) -> None:
    monkeypatch.setattr("app.chesscom.services.enqueue_chesscom_sync_job", lambda _: None)


def connect_account(
    monkeypatch,
    user_data: dict,
    username: str | None = None,
    profile_username: str | None = None,
) -> dict:
    resolved_profile_username = profile_username or unique_chesscom_username()
    resolved_username = username or f"https://www.chess.com/member/{resolved_profile_username}/"
    monkeypatch.setattr(
        "app.chesscom.services.get_chesscom_api_client",
        lambda: FakeChessComClient(profile_username=resolved_profile_username),
    )
    response = client.post(
        "/api/v1/integrations/chesscom/connect",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"username": resolved_username},
    )
    assert response.status_code == 200, response.text
    return response.json()


def request_sync(monkeypatch, user_data: dict, months: int | None = 3) -> dict:
    disable_chesscom_queue(monkeypatch)
    response = client.post(
        "/api/v1/integrations/chesscom/sync",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"months": months} if months is not None else {},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _sync_job_status(job_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        job = await session.get(ChessComSyncJob, uuid.UUID(job_id))
        assert job is not None
        return {
            "status": job.status,
            "games_found": job.games_found,
            "games_imported": job.games_imported,
            "games_skipped": job.games_skipped,
            "error_message": job.error_message,
        }


async def _counts_for_imported_game(game_id: str) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        game_count = await session.scalar(
            select(func.count()).select_from(Game).where(Game.id == uuid.UUID(game_id))
        )
        move_count = await session.scalar(
            select(func.count()).select_from(GameMove).where(GameMove.game_id == uuid.UUID(game_id))
        )
        pgn_import_count = await session.scalar(
            select(func.count())
            .select_from(PgnImport)
            .where(PgnImport.game_id == uuid.UUID(game_id), PgnImport.source == "chesscom")
        )
        imported_count = await session.scalar(
            select(func.count())
            .select_from(ChessComImportedGame)
            .where(ChessComImportedGame.game_id == uuid.UUID(game_id))
        )
        return {
            "games": game_count or 0,
            "moves": move_count or 0,
            "pgn_imports": pgn_import_count or 0,
            "imported_games": imported_count or 0,
        }


async def _latest_imported_game_id(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChessComImportedGame.game_id)
            .where(ChessComImportedGame.user_id == uuid.UUID(user_id))
            .order_by(ChessComImportedGame.created_at.desc())
            .limit(1)
        )
        return str(result.scalar_one())


def run_fake_sync(job_id: str, fake_client: FakeChessComClient | None = None) -> None:
    asyncio.run(run_chesscom_sync_job_async(uuid.UUID(job_id), api_client=fake_client))


def import_one_chesscom_game(
    monkeypatch,
    user_data: dict,
    game_payload: dict[str, Any] | None = None,
) -> str:
    connect_account(monkeypatch, user_data)
    job = request_sync(monkeypatch, user_data)
    archive = "https://api.chess.com/pub/player/ibra0hh/games/2026/05"
    run_fake_sync(
        job["id"],
        FakeChessComClient(
            archives=[archive],
            games_by_archive={archive: [game_payload or mock_chesscom_game()]},
        ),
    )
    return asyncio.run(_latest_imported_game_id(user_data["user"]["id"]))


def test_authenticated_user_can_connect_chesscom_username(monkeypatch) -> None:
    user_data = register_user()
    profile_username = unique_chesscom_username()

    account = connect_account(monkeypatch, user_data, profile_username=profile_username)

    assert account["username"] == profile_username.lower()
    assert account["profile_url"] == f"https://www.chess.com/member/{profile_username}"
    assert account["verified"] is True


def test_unauthenticated_user_cannot_connect() -> None:
    response = client.post(
        "/api/v1/integrations/chesscom/connect",
        json={"username": "Ibra0hh"},
    )

    assert response.status_code == 401


def test_username_normalization_works(monkeypatch) -> None:
    user_data = register_user()
    profile_username = unique_chesscom_username("IBRA0HH")

    account = connect_account(
        monkeypatch,
        user_data,
        username=f" https://www.chess.com/member/{profile_username}/ ",
        profile_username=profile_username,
    )

    assert account["username"] == profile_username.lower()


def test_user_can_fetch_own_connected_account(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)

    response = client.get(
        "/api/v1/integrations/chesscom/account",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["username"].startswith("ibra0hh_")


def test_user_can_disconnect_own_account(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)

    response = client.delete(
        "/api/v1/integrations/chesscom/account",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )
    account_response = client.get(
        "/api/v1/integrations/chesscom/account",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 204
    assert account_response.status_code == 200
    assert account_response.json() is None


def test_duplicate_username_conflict_handled_cleanly(monkeypatch) -> None:
    first = register_user("chesscom-first")
    second = register_user("chesscom-second")
    taken_username = unique_chesscom_username("TakenUser")
    connect_account(monkeypatch, first, username=taken_username, profile_username=taken_username)
    monkeypatch.setattr(
        "app.chesscom.services.get_chesscom_api_client",
        lambda: FakeChessComClient(profile_username=taken_username),
    )

    response = client.post(
        "/api/v1/integrations/chesscom/connect",
        headers=auth_headers(second["tokens"]["access_token"]),
        json={"username": taken_username.lower()},
    )

    assert response.status_code == 409


def test_user_can_request_sync(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)

    job = request_sync(monkeypatch, user_data, months=2)

    assert job["status"] == "queued"
    assert job["archive_months_requested"] == 2


def test_unauthenticated_user_cannot_request_sync() -> None:
    response = client.post("/api/v1/integrations/chesscom/sync", json={"months": 1})

    assert response.status_code == 401


def test_existing_queued_sync_returns_existing_job(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)
    first = request_sync(monkeypatch, user_data)

    second = request_sync(monkeypatch, user_data)

    assert second["id"] == first["id"]


def test_requested_months_capped_by_config(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)

    job = request_sync(monkeypatch, user_data, months=99)

    assert job["archive_months_requested"] == 3


def test_user_can_list_own_sync_jobs(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)
    job = request_sync(monkeypatch, user_data)

    response = client.get(
        "/api/v1/integrations/chesscom/sync-jobs",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert job["id"] in {item["id"] for item in response.json()["items"]}


def test_user_cannot_view_another_users_sync_job(monkeypatch) -> None:
    owner = register_user("chesscom-owner")
    other = register_user("chesscom-other")
    connect_account(monkeypatch, owner)
    job = request_sync(monkeypatch, owner)

    response = client.get(
        f"/api/v1/integrations/chesscom/sync-jobs/{job['id']}",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_admin_can_list_sync_jobs(monkeypatch) -> None:
    owner = register_user("chesscom-owner")
    admin = register_admin()
    connect_account(monkeypatch, owner)
    job = request_sync(monkeypatch, owner)

    response = client.get(
        "/api/v1/admin/chesscom/sync-jobs",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert job["id"] in {item["id"] for item in response.json()["items"]}


def test_worker_imports_mocked_chesscom_pgn_game(monkeypatch) -> None:
    user_data = register_user()
    game_id = import_one_chesscom_game(monkeypatch, user_data)

    counts = asyncio.run(_counts_for_imported_game(game_id))

    assert counts["games"] == 1
    assert counts["moves"] == 6
    assert counts["pgn_imports"] == 1
    assert counts["imported_games"] == 1


def test_duplicate_chesscom_url_is_skipped(monkeypatch) -> None:
    user_data = register_user()
    duplicate_url = f"https://www.chess.com/game/live/{unique_suffix()}"
    import_one_chesscom_game(monkeypatch, user_data, mock_chesscom_game(url=duplicate_url))
    job = request_sync(monkeypatch, user_data)
    archive = "https://api.chess.com/pub/player/ibra0hh/games/2026/05"

    run_fake_sync(
        job["id"],
        FakeChessComClient(
            archives=[archive],
            games_by_archive={archive: [mock_chesscom_game(url=duplicate_url)]},
        ),
    )

    status_data = asyncio.run(_sync_job_status(job["id"]))
    assert status_data["games_found"] == 1
    assert status_data["games_imported"] == 0
    assert status_data["games_skipped"] == 1


def test_invalid_pgn_is_skipped_and_counted(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)
    job = request_sync(monkeypatch, user_data)
    archive = "https://api.chess.com/pub/player/ibra0hh/games/2026/05"

    run_fake_sync(
        job["id"],
        FakeChessComClient(
            archives=[archive],
            games_by_archive={archive: [mock_chesscom_game(pgn="not a valid game")]},
        ),
    )

    status_data = asyncio.run(_sync_job_status(job["id"]))
    assert status_data["status"] == "completed"
    assert status_data["games_found"] == 1
    assert status_data["games_imported"] == 0
    assert status_data["games_skipped"] == 1


def test_job_failure_sets_status_failed_safely(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)
    job = request_sync(monkeypatch, user_data)

    run_fake_sync(job["id"], FakeChessComClient(fail_archives=True))

    status_data = asyncio.run(_sync_job_status(job["id"]))
    assert status_data["status"] == "failed"
    assert "traceback" not in str(status_data["error_message"]).lower()


def test_job_completes_with_correct_counts(monkeypatch) -> None:
    user_data = register_user()
    connect_account(monkeypatch, user_data)
    job = request_sync(monkeypatch, user_data)
    archive = "https://api.chess.com/pub/player/ibra0hh/games/2026/05"

    run_fake_sync(
        job["id"],
        FakeChessComClient(
            archives=[archive],
            games_by_archive={
                archive: [
                    mock_chesscom_game(),
                    mock_chesscom_game(pgn="not a valid game"),
                ]
            },
        ),
    )

    status_data = asyncio.run(_sync_job_status(job["id"]))
    assert status_data["status"] == "completed"
    assert status_data["games_found"] == 2
    assert status_data["games_imported"] == 1
    assert status_data["games_skipped"] == 1


def test_imported_chesscom_games_appear_in_game_library(monkeypatch) -> None:
    user_data = register_user()
    game_id = import_one_chesscom_game(monkeypatch, user_data)

    response = client.get(
        "/api/v1/games?source=chesscom_import",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert game_id in {item["id"] for item in response.json()["items"]}


def test_user_can_view_own_imported_game_detail(monkeypatch) -> None:
    user_data = register_user()
    game_id = import_one_chesscom_game(monkeypatch, user_data)

    response = client.get(
        f"/api/v1/games/{game_id}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["source"] == "chesscom_import"
    assert response.json()["moves"][0]["uci"] == "e2e4"


def test_user_cannot_view_another_users_imported_game(monkeypatch) -> None:
    owner = register_user("chesscom-owner")
    other = register_user("chesscom-other")
    game_id = import_one_chesscom_game(monkeypatch, owner)

    response = client.get(
        f"/api/v1/games/{game_id}",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_imported_game_can_use_existing_analysis_endpoint(monkeypatch) -> None:
    user_data = register_user()
    game_id = import_one_chesscom_game(monkeypatch, user_data)
    monkeypatch.setattr("app.analysis.services.enqueue_analysis_job", lambda _: None)

    response = client.post(
        f"/api/v1/games/{game_id}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"depth": 10},
    )

    assert response.status_code == 201
    assert response.json()["game_id"] == game_id


def test_user_can_list_own_import_history(monkeypatch) -> None:
    user_data = register_user()
    import_one_chesscom_game(monkeypatch, user_data)

    response = client.get(
        "/api/v1/pgn-imports",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert "chesscom" in {item["source"] for item in response.json()["items"]}


def test_user_can_list_own_chesscom_imported_games(monkeypatch) -> None:
    user_data = register_user()
    game_id = import_one_chesscom_game(monkeypatch, user_data)

    response = client.get(
        "/api/v1/integrations/chesscom/imported-games",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert game_id in {item["game_id"] for item in response.json()["items"]}


def test_admin_can_list_chesscom_accounts_and_imported_games(monkeypatch) -> None:
    owner = register_user("chesscom-owner")
    admin = register_admin()
    game_id = import_one_chesscom_game(monkeypatch, owner)

    accounts_response = client.get(
        "/api/v1/admin/chesscom/accounts",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    imported_response = client.get(
        "/api/v1/admin/chesscom/imported-games",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert accounts_response.status_code == 200
    assert imported_response.status_code == 200
    assert owner["user"]["id"] in {item["user_id"] for item in accounts_response.json()["items"]}
    assert game_id in {item["game_id"] for item in imported_response.json()["items"]}


def test_member_cannot_access_admin_chesscom_endpoints() -> None:
    member = register_user()

    accounts_response = client.get(
        "/api/v1/admin/chesscom/accounts",
        headers=auth_headers(member["tokens"]["access_token"]),
    )
    jobs_response = client.get(
        "/api/v1/admin/chesscom/sync-jobs",
        headers=auth_headers(member["tokens"]["access_token"]),
    )
    imported_response = client.get(
        "/api/v1/admin/chesscom/imported-games",
        headers=auth_headers(member["tokens"]["access_token"]),
    )

    assert accounts_response.status_code == 403
    assert jobs_response.status_code == 403
    assert imported_response.status_code == 403
