import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import chess
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analysis.engine import PositionAnalysis, format_cp_evaluation
from app.analysis.tasks import run_analysis_job_async
from app.auth.models import Role, UserRole
from app.chesscom.models import ChessComAccount, ChessComSyncJob
from app.chesscom.tasks import run_chesscom_sync_job_async
from app.common.time import utc_now
from app.database import AsyncSessionLocal
from app.main import app
from app.notifications.models import Notification, NotificationPreference
from app.notifications.services import create_user_notification
from app.realtime.models import RealtimeEvent
from app.realtime.services import list_stream_events_for_user

client = TestClient(app)

VALID_PGN = """[Event "Notification Analysis"]
[Site "Amman"]
[Date "2026.05.19"]
[Round "1"]
[White "Ibrahim"]
[Black "Dana"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""


class FakeEngine:
    version = "Fakefish Notifications"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.index = 0
        self.scores = [40, 35, 20, 15, 30, 25, 10, 5]

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
            raise RuntimeError("fake engine failed safely")
        value = self.scores[self.index] if self.index < len(self.scores) else 0
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


class FakeChessComClient:
    def __init__(self, fail_archives: bool = False) -> None:
        self.fail_archives = fail_archives

    async def fetch_archives(self, username: str) -> list[str]:
        _ = username
        if self.fail_archives:
            raise RuntimeError("public api unavailable")
        return []

    async def fetch_archive_games(self, archive_url: str) -> list[dict[str, Any]]:
        _ = archive_url
        return []


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def unique_user_payload(prefix: str = "notify-test") -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"{prefix.replace('-', '_')}_{suffix}",
        "full_name": "Notification Test User",
    }


def register_user(prefix: str = "notify-test") -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload(prefix))
    assert response.status_code == 201, response.text
    return response.json()


async def _assign_role(user_id: uuid.UUID, role_name: str) -> None:
    async with AsyncSessionLocal() as session:
        role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one()
        session.add(UserRole(user_id=user_id, role_id=role.id))
        await session.commit()


def assign_role(user_id: str, role_name: str) -> None:
    asyncio.run(_assign_role(uuid.UUID(user_id), role_name))


def register_admin() -> dict:
    data = register_user("notify-admin")
    assign_role(data["user"]["id"], "admin")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": data["user"]["email"], "password": "correct-horse-123"},
    )
    assert login_response.status_code == 200, login_response.text
    data["tokens"] = login_response.json()["tokens"]
    return data


async def _create_notification(user_id: str, notification_type: str = "message.received") -> str:
    async with AsyncSessionLocal() as session:
        notification = await create_user_notification(
            session,
            user_id=uuid.UUID(user_id),
            notification_type=notification_type,
            title="Test notification",
            body="Body",
            data={"message_id": uuid.uuid4(), "password": "secret"},
        )
        await session.commit()
        assert notification is not None
        return str(notification.id)


async def _notification_count(user_id: str, notification_type: str | None = None) -> int:
    async with AsyncSessionLocal() as session:
        statement = select(Notification).where(Notification.user_id == uuid.UUID(user_id))
        if notification_type is not None:
            statement = statement.where(Notification.type == notification_type)
        result = await session.execute(statement)
        return len(list(result.scalars()))


def send_friend_request(sender: dict, receiver: dict) -> dict:
    response = client.post(
        "/api/v1/friends/requests",
        headers=auth_headers(sender["tokens"]["access_token"]),
        json={"receiver_id": receiver["user"]["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept_friend_request(receiver: dict, request_id: str) -> dict:
    response = client.post(
        f"/api/v1/friends/requests/{request_id}/accept",
        headers=auth_headers(receiver["tokens"]["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def make_friends() -> tuple[dict, dict]:
    sender = register_user("notify-sender")
    receiver = register_user("notify-receiver")
    request = send_friend_request(sender, receiver)
    accept_friend_request(receiver, request["id"])
    return sender, receiver


def create_direct_conversation(user: dict, other: dict) -> dict:
    response = client.post(
        "/api/v1/conversations/direct",
        headers=auth_headers(user["tokens"]["access_token"]),
        json={"user_id": other["user"]["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def send_message(sender: dict, conversation_id: str, body: str = "Realtime hello") -> dict:
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(sender["tokens"]["access_token"]),
        json={"body": body},
    )
    assert response.status_code == 200, response.text
    return response.json()


def paste_pgn(user_data: dict) -> dict:
    response = client.post(
        "/api/v1/games/pgn/paste",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"pgn_text": VALID_PGN},
    )
    assert response.status_code == 201, response.text
    return response.json()


def disable_analysis_queue(monkeypatch) -> None:
    monkeypatch.setattr("app.analysis.services.enqueue_analysis_job", lambda _: None)


def request_analysis(monkeypatch, user_data: dict, game_id: str) -> dict:
    disable_analysis_queue(monkeypatch)
    response = client.post(
        f"/api/v1/games/{game_id}/analysis",
        headers=auth_headers(user_data["tokens"]["access_token"]),
        json={"depth": 10},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_chesscom_sync_job(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        account = ChessComAccount(
            user_id=uuid.UUID(user_id),
            username=f"notify_{unique_suffix()}",
            verified=True,
        )
        session.add(account)
        await session.flush()
        job = ChessComSyncJob(
            user_id=uuid.UUID(user_id),
            chesscom_account_id=account.id,
            status="queued",
            archive_months_requested=1,
        )
        session.add(job)
        await session.commit()
        return str(job.id)


def test_user_can_list_own_notifications() -> None:
    user = register_user()
    asyncio.run(_create_notification(user["user"]["id"]))

    response = client.get(
        "/api/v1/notifications",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Test notification"


def test_user_cannot_access_another_users_notification() -> None:
    owner = register_user("notify-owner")
    other = register_user("notify-other")
    notification_id = asyncio.run(_create_notification(owner["user"]["id"]))

    response = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=auth_headers(other["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_user_can_mark_notification_read() -> None:
    user = register_user()
    notification_id = asyncio.run(_create_notification(user["user"]["id"]))

    response = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["read_at"] is not None


def test_user_can_mark_all_notifications_read_and_unread_count_works() -> None:
    user = register_user()
    asyncio.run(_create_notification(user["user"]["id"]))
    asyncio.run(_create_notification(user["user"]["id"], "friend_request.received"))

    unread_response = client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_headers(user["tokens"]["access_token"]),
    )
    read_all_response = client.post(
        "/api/v1/notifications/read-all",
        headers=auth_headers(user["tokens"]["access_token"]),
    )
    unread_after_response = client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert unread_response.json()["unread_count"] == 2
    assert read_all_response.json()["marked_read"] == 2
    assert unread_after_response.json()["unread_count"] == 0


def test_notification_preferences_are_created_and_defaulted() -> None:
    user = register_user()

    response = client.get(
        "/api/v1/notifications/preferences",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["in_app_enabled"] is True
    assert response.json()["chat_messages"] is True


def test_user_can_update_notification_preferences() -> None:
    user = register_user()

    response = client.patch(
        "/api/v1/notifications/preferences",
        headers=auth_headers(user["tokens"]["access_token"]),
        json={"chat_messages": False, "analysis_updates": False},
    )

    assert response.status_code == 200
    assert response.json()["chat_messages"] is False
    assert response.json()["analysis_updates"] is False


def test_admin_can_list_notifications_and_member_cannot() -> None:
    user = register_user()
    admin = register_admin()
    asyncio.run(_create_notification(user["user"]["id"]))

    admin_response = client.get(
        "/api/v1/admin/notifications",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    member_response = client.get(
        "/api/v1/admin/notifications",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert admin_response.status_code == 200
    assert admin_response.json()["total"] >= 1
    assert member_response.status_code == 403


def test_friend_request_creates_notification_for_receiver() -> None:
    sender = register_user("notify-friend-sender")
    receiver = register_user("notify-friend-receiver")

    request = send_friend_request(sender, receiver)
    notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(receiver["tokens"]["access_token"]),
    ).json()["items"]

    assert notifications[0]["type"] == "friend_request.received"
    assert notifications[0]["data"]["friend_request_id"] == request["id"]
    assert notifications[0]["data"]["sender_id"] == sender["user"]["id"]


def test_accepting_friend_request_creates_notification_for_sender() -> None:
    sender = register_user("notify-accept-sender")
    receiver = register_user("notify-accept-receiver")
    request = send_friend_request(sender, receiver)

    accept_friend_request(receiver, request["id"])
    notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(sender["tokens"]["access_token"]),
    ).json()["items"]

    assert notifications[0]["type"] == "friend_request.accepted"
    assert notifications[0]["data"]["friend_request_id"] == request["id"]


def test_sending_direct_message_creates_safe_notification_for_recipient() -> None:
    sender, receiver = make_friends()
    conversation = create_direct_conversation(sender, receiver)
    message = send_message(sender, conversation["id"])

    notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(receiver["tokens"]["access_token"]),
    ).json()["items"]

    assert notifications[0]["type"] == "message.received"
    assert notifications[0]["data"]["conversation_id"] == conversation["id"]
    assert notifications[0]["data"]["message_id"] == message["id"]
    assert "body" not in notifications[0]["data"]
    assert "password" not in str(notifications[0]["data"]).lower()


def test_analysis_completed_creates_notification(monkeypatch) -> None:
    user = register_user("notify-analysis-complete")
    game = paste_pgn(user)
    job = request_analysis(monkeypatch, user, game["id"])

    asyncio.run(
        run_analysis_job_async(
            uuid.UUID(job["id"]),
            analyzer_factory=lambda: FakeEngine(),
        )
    )

    notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(user["tokens"]["access_token"]),
    ).json()["items"]
    assert notifications[0]["type"] == "analysis.completed"
    assert notifications[0]["data"]["analysis_job_id"] == job["id"]


def test_analysis_failed_creates_notification(monkeypatch) -> None:
    user = register_user("notify-analysis-fail")
    game = paste_pgn(user)
    job = request_analysis(monkeypatch, user, game["id"])

    asyncio.run(
        run_analysis_job_async(
            uuid.UUID(job["id"]),
            analyzer_factory=lambda: FakeEngine(fail=True),
        )
    )

    notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(user["tokens"]["access_token"]),
    ).json()["items"]
    assert notifications[0]["type"] == "analysis.failed"
    assert notifications[0]["data"]["analysis_job_id"] == job["id"]


def test_chesscom_sync_completed_and_failed_create_notifications() -> None:
    completed_user = register_user("notify-chesscom-complete")
    failed_user = register_user("notify-chesscom-fail")
    completed_job_id = asyncio.run(_create_chesscom_sync_job(completed_user["user"]["id"]))
    failed_job_id = asyncio.run(_create_chesscom_sync_job(failed_user["user"]["id"]))

    asyncio.run(run_chesscom_sync_job_async(uuid.UUID(completed_job_id), FakeChessComClient()))
    asyncio.run(
        run_chesscom_sync_job_async(
            uuid.UUID(failed_job_id),
            FakeChessComClient(fail_archives=True),
        )
    )

    completed_notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(completed_user["tokens"]["access_token"]),
    ).json()["items"]
    failed_notifications = client.get(
        "/api/v1/notifications",
        headers=auth_headers(failed_user["tokens"]["access_token"]),
    ).json()["items"]
    assert completed_notifications[0]["type"] == "chesscom.sync_completed"
    assert failed_notifications[0]["type"] == "chesscom.sync_failed"


def test_realtime_event_created_for_notification_and_visible_to_owner_only() -> None:
    owner = register_user("notify-realtime-owner")
    other = register_user("notify-realtime-other")
    asyncio.run(_create_notification(owner["user"]["id"]))

    async def load_events() -> tuple[int, int]:
        async with AsyncSessionLocal() as session:
            since = utc_now() - timedelta(minutes=5)
            owner_events = await list_stream_events_for_user(
                session,
                user_id=uuid.UUID(owner["user"]["id"]),
                after_created_at=since,
            )
            other_events = await list_stream_events_for_user(
                session,
                user_id=uuid.UUID(other["user"]["id"]),
                after_created_at=since,
            )
            return len(owner_events), len(other_events)

    owner_count, other_count = asyncio.run(load_events())

    assert owner_count >= 1
    assert other_count == 0


def test_admin_can_list_realtime_events_and_member_cannot() -> None:
    user = register_user("notify-realtime-member")
    admin = register_admin()
    asyncio.run(_create_notification(user["user"]["id"]))

    admin_response = client.get(
        "/api/v1/admin/realtime/events",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    member_response = client.get(
        "/api/v1/admin/realtime/events",
        headers=auth_headers(user["tokens"]["access_token"]),
    )

    assert admin_response.status_code == 200
    assert admin_response.json()["total"] >= 1
    assert member_response.status_code == 403


def test_disabled_chat_messages_preference_suppresses_message_notification() -> None:
    sender, receiver = make_friends()
    client.patch(
        "/api/v1/notifications/preferences",
        headers=auth_headers(receiver["tokens"]["access_token"]),
        json={"chat_messages": False},
    )
    conversation = create_direct_conversation(sender, receiver)

    send_message(sender, conversation["id"])

    assert asyncio.run(_notification_count(receiver["user"]["id"], "message.received")) == 0


def test_disabled_in_app_preference_suppresses_notification() -> None:
    user = register_user("notify-disabled")
    client.patch(
        "/api/v1/notifications/preferences",
        headers=auth_headers(user["tokens"]["access_token"]),
        json={"in_app_enabled": False},
    )

    async def try_create_notification() -> int:
        async with AsyncSessionLocal() as session:
            await create_user_notification(
                session,
                user_id=uuid.UUID(user["user"]["id"]),
                notification_type="friend_request.received",
                title="Suppressed",
            )
            await session.commit()
            count = await session.scalar(
                select(Notification).where(Notification.user_id == uuid.UUID(user["user"]["id"]))
            )
            return 1 if count else 0

    assert asyncio.run(try_create_notification()) == 0


def test_notification_data_redacts_sensitive_keys() -> None:
    user = register_user("notify-redact")
    notification_id = asyncio.run(_create_notification(user["user"]["id"]))

    async def load_data() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            notification = await session.get(Notification, uuid.UUID(notification_id))
            assert notification is not None
            return notification.data

    data = asyncio.run(load_data())

    assert data["password"] == "[redacted]"


def test_notification_preferences_row_created_on_registration() -> None:
    user = register_user("notify-pref-row")

    async def preference_exists() -> bool:
        async with AsyncSessionLocal() as session:
            preferences = await session.get(
                NotificationPreference,
                uuid.UUID(user["user"]["id"]),
            )
            return preferences is not None and preferences.in_app_enabled

    assert asyncio.run(preference_exists()) is True


def test_broadcast_realtime_event_created_when_news_or_announcement_published() -> None:
    admin = register_admin()
    article_response = client.post(
        "/api/v1/admin/news",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={
            "title": f"Realtime News {unique_suffix()}",
            "summary": "Realtime summary",
            "body_markdown": "Realtime body",
        },
    )
    assert article_response.status_code == 201, article_response.text
    publish_response = client.post(
        f"/api/v1/admin/news/{article_response.json()['id']}/publish",
        headers=auth_headers(admin["tokens"]["access_token"]),
    )
    announcement_response = client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(admin["tokens"]["access_token"]),
        json={
            "title": f"Realtime Announcement {unique_suffix()}",
            "message": "Realtime message",
            "target": "all",
            "priority": "normal",
            "status": "published",
        },
    )

    async def event_types() -> set[str]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RealtimeEvent.type).where(
                    RealtimeEvent.created_at > datetime(2026, 1, 1, tzinfo=UTC)
                )
            )
            return set(result.scalars())

    assert publish_response.status_code == 200
    assert announcement_response.status_code == 201
    types = asyncio.run(event_types())
    assert "news.published" in types
    assert "announcement.published" in types


def test_sse_endpoint_requires_auth_and_rejects_invalid_token() -> None:
    no_auth_response = client.get("/api/v1/realtime/stream")
    invalid_auth_response = client.get(
        "/api/v1/realtime/stream",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert no_auth_response.status_code == 401
    assert invalid_auth_response.status_code == 401
