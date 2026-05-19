import asyncio
import uuid

import chess
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.analysis.engine import (
    PositionAnalysis,
    classify_centipawn_loss,
    format_cp_evaluation,
    format_mate_evaluation,
)
from app.analysis.models import AnalysisJob, AnalysisMoveEvaluation, AnalysisReport
from app.analysis.tasks import run_analysis_job_async
from app.auth.models import Role, UserRole
from app.database import AsyncSessionLocal
from app.games.models import Game
from app.main import app

client = TestClient(app)

VALID_PGN = """[Event "Analysis Test"]
[Site "Amman"]
[Date "2026.05.19"]
[Round "1"]
[White "Ibrahim"]
[Black "Dana"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


class FakeEngine:
    version = "Fakefish 1.0"

    def __init__(self, scores: list[int] | None = None, fail: bool = False) -> None:
        self.scores = scores or [100, 95, 80, 40, 120, 100, 50, -50, 60, 58, 10, -400]
        self.index = 0
        self.fail = fail

    def __enter__(self) -> "FakeEngine":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def analyze(
        self,
        board: chess.Board,
        depth: int,
        pov_color: chess.Color,
    ) -> PositionAnalysis:
        _ = depth, pov_color
        if self.fail:
            raise RuntimeError("engine failed without exposing internals")
        value = self.scores[self.index] if self.index < len(self.scores) else 25
        self.index += 1
        best_move = next(iter(board.legal_moves), None)
        best_move_uci = best_move.uci() if best_move else None
        best_move_san = board.san(best_move) if best_move else None
        return PositionAnalysis(
            evaluation=format_cp_evaluation(value),
            side_score_cp=value,
            best_move_uci=best_move_uci,
            best_move_san=best_move_san,
            principal_variation=[best_move_uci] if best_move_uci else [],
        )


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "analysis-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Analysis Test User",
    }


def register_user(prefix: str = "analysis-test") -> dict:
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
    data = register_user("analysis-admin")
    assign_role(data["user"]["id"], "admin")
    return data


def disable_queue(monkeypatch) -> None:
    monkeypatch.setattr("app.analysis.services.enqueue_analysis_job", lambda _: None)


def paste_pgn(user_data: dict, pgn_text: str = VALID_PGN) -> dict:
    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": pgn_text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def request_analysis(
    monkeypatch,
    user_data: dict,
    game_id: str,
    depth: int | None = 10,
) -> dict:
    disable_queue(monkeypatch)
    response = client.post(
        f"/api/v1/games/{game_id}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"depth": depth} if depth is not None else {},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_game_without_moves(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        game = Game(
            owner_id=uuid.UUID(user_id),
            source="manual",
            white_name="Empty",
            black_name="Game",
            result="*",
        )
        session.add(game)
        await session.commit()
        await session.refresh(game)
        return str(game.id)


async def _count_reports(job_id: str) -> int:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(AnalysisReport)
            .where(AnalysisReport.analysis_job_id == uuid.UUID(job_id))
        )
        return count or 0


async def _count_move_evaluations(job_id: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AnalysisReport).where(AnalysisReport.analysis_job_id == uuid.UUID(job_id))
        )
        report = result.scalar_one()
        count = await session.scalar(
            select(func.count())
            .select_from(AnalysisMoveEvaluation)
            .where(AnalysisMoveEvaluation.analysis_report_id == report.id)
        )
        return count or 0


async def _job_status(job_id: str) -> str:
    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, uuid.UUID(job_id))
        assert job is not None
        return job.status


def run_fake_job(job_id: str, fail: bool = False) -> None:
    asyncio.run(
        run_analysis_job_async(
            uuid.UUID(job_id),
            analyzer_factory=lambda: FakeEngine(fail=fail),
        )
    )


def latest_report_for_game(user_data: dict, game_id: str) -> dict:
    response = client.get(
        f"/api/v1/games/{game_id}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    report = response.json()["report"]
    assert report is not None
    return report


def test_user_can_request_analysis_for_own_uploaded_game(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)

    job = request_analysis(monkeypatch, user_data, game["id"])

    assert job["game_id"] == game["id"]
    assert job["status"] == "queued"
    assert job["engine_name"] == "stockfish"


def test_user_cannot_request_analysis_for_another_users_private_game(monkeypatch) -> None:
    owner = register_user("analysis-owner")
    other = register_user("analysis-other")
    game = paste_pgn(owner)
    disable_queue(monkeypatch)

    response = client.post(
        f"/api/v1/games/{game['id']}/analysis",
        headers=auth_headers(other["tokens"]["access_token"]),
        json={"depth": 10},
    )

    assert response.status_code == 404


def test_admin_can_request_analysis_for_any_game(monkeypatch) -> None:
    owner = register_user("analysis-owner")
    admin = register_admin()
    game = paste_pgn(owner)

    job = request_analysis(monkeypatch, admin, game["id"])

    assert job["game_id"] == game["id"]


def test_duplicate_queued_job_returns_existing_job(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    first = request_analysis(monkeypatch, user_data, game["id"])
    second = request_analysis(monkeypatch, user_data, game["id"])

    assert second["id"] == first["id"]
    assert second["status"] == "queued"


def test_completed_report_is_returned_instead_of_duplicate_job(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])
    run_fake_job(job["id"])

    second = request_analysis(monkeypatch, user_data, game["id"])

    assert second["id"] == job["id"]
    assert second["status"] == "completed"


def test_invalid_depth_rejected(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    disable_queue(monkeypatch)

    response = client.post(
        f"/api/v1/games/{game['id']}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"depth": 99},
    )

    assert response.status_code == 422


def test_game_with_no_moves_rejected(monkeypatch) -> None:
    user_data = register_user()
    game_id = asyncio.run(_create_game_without_moves(user_data["user"]["id"]))
    disable_queue(monkeypatch)

    response = client.post(
        f"/api/v1/games/{game_id}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"depth": 10},
    )

    assert response.status_code == 400


def test_worker_completes_job_and_creates_report_and_evaluations(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])

    run_fake_job(job["id"])

    assert asyncio.run(_job_status(job["id"])) == "completed"
    assert asyncio.run(_count_reports(job["id"])) == 1
    assert asyncio.run(_count_move_evaluations(job["id"])) == len(game["moves"])


def test_failed_engine_analysis_marks_job_failed_safely(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])

    run_fake_job(job["id"], fail=True)

    response = client.get(
        f"/api/v1/analysis/jobs/{job['id']}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "traceback" not in response.text.lower()
    assert asyncio.run(_count_reports(job["id"])) == 0


def test_get_job_returns_status(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])

    response = client.get(
        f"/api/v1/analysis/jobs/{job['id']}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_get_game_analysis_returns_job_status_when_not_completed(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])

    response = client.get(
        f"/api/v1/games/{game['id']}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["report"] is None
    assert response.json()["job"]["id"] == job["id"]


def test_get_game_analysis_returns_report_when_completed(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])
    run_fake_job(job["id"])

    report = latest_report_for_game(user_data, game["id"])

    assert report["moves"]
    assert report["summary"]["total_plies"] == len(game["moves"])
    assert report["white_accuracy"] is not None


def test_get_report_returns_move_evaluations_ordered_by_ply(monkeypatch) -> None:
    user_data = register_user()
    game = paste_pgn(user_data)
    job = request_analysis(monkeypatch, user_data, game["id"])
    run_fake_job(job["id"])
    report = latest_report_for_game(user_data, game["id"])

    response = client.get(
        f"/api/v1/analysis/reports/{report['id']}",
        headers=auth_headers(user_data["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    ply_numbers = [move["ply_number"] for move in response.json()["moves"]]
    assert ply_numbers == sorted(ply_numbers)
    assert response.json()["moves"][0]["best_move_uci"]


def test_admin_can_list_jobs_and_reports(monkeypatch) -> None:
    owner = register_user("analysis-owner")
    admin = register_admin()
    game = paste_pgn(owner)
    job = request_analysis(monkeypatch, owner, game["id"])
    run_fake_job(job["id"])

    jobs_response = client.get(
        "/api/v1/admin/analysis/jobs",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    reports_response = client.get(
        "/api/v1/admin/analysis/reports",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )

    assert jobs_response.status_code == 200
    assert reports_response.status_code == 200
    assert job["id"] in {item["id"] for item in jobs_response.json()["items"]}
    assert game["id"] in {item["game_id"] for item in reports_response.json()["items"]}


def test_member_cannot_access_admin_analysis_endpoints() -> None:
    member = register_user()

    jobs_response = client.get(
        "/api/v1/admin/analysis/jobs",
        headers=auth_headers(member["tokens"]["access_token"]),
    )
    reports_response = client.get(
        "/api/v1/admin/analysis/reports",
        headers=auth_headers(member["tokens"]["access_token"]),
    )

    assert jobs_response.status_code == 403
    assert reports_response.status_code == 403


def test_classification_function_maps_centipawn_losses() -> None:
    assert classify_centipawn_loss(0) == "best"
    assert classify_centipawn_loss(20) == "excellent"
    assert classify_centipawn_loss(50) == "good"
    assert classify_centipawn_loss(100) == "inaccuracy"
    assert classify_centipawn_loss(200) == "mistake"
    assert classify_centipawn_loss(301) == "blunder"
    assert classify_centipawn_loss(None) == "unknown"


def test_evaluation_format_handles_cp_and_mate_values() -> None:
    assert format_cp_evaluation(35) == {"type": "cp", "value": 35, "display": "+0.35"}
    assert format_mate_evaluation(3) == {"type": "mate", "value": 3, "display": "M3"}
    assert format_mate_evaluation(-2) == {"type": "mate", "value": -2, "display": "-M2"}
