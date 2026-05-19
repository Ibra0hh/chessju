import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admin.models import AdminActionLog
from app.auth.models import Role, UserRole
from app.database import AsyncSessionLocal
from app.main import app
from app.social.models import FriendRequest, Friendship, Message

client = TestClient(app)


def unique_user_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:12]
    return {
        "email": f"social-{suffix}@example.com",
        "password": "correct-horse-123",
        "username": f"social_{suffix}",
        "full_name": "ChessJU Social User",
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_user() -> dict:
    response = client.post("/api/v1/auth/register", json=unique_user_payload())
    assert response.status_code == 201, response.text
    data = response.json()
    return {
        "id": data["user"]["id"],
        "headers": auth_headers(data["tokens"]["access_token"]),
        "data": data,
    }


def register_admin() -> dict:
    admin = register_user()

    async def assign_admin_role() -> None:
        async with AsyncSessionLocal() as session:
            role = (
                await session.execute(select(Role).where(Role.name == "admin"))
            ).scalar_one()
            session.add(
                UserRole(
                    user_id=uuid.UUID(admin["id"]),
                    role_id=role.id,
                    assigned_by=None,
                )
            )
            await session.commit()

    asyncio.run(assign_admin_role())
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin["data"]["user"]["email"],
            "password": "correct-horse-123",
        },
    )
    assert login_response.status_code == 200, login_response.text
    admin["headers"] = auth_headers(login_response.json()["tokens"]["access_token"])
    return admin


def send_request(sender: dict, receiver: dict) -> dict:
    response = client.post(
        "/api/v1/friends/requests",
        headers=sender["headers"],
        json={"receiver_id": receiver["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept_request(receiver: dict, request_id: str) -> dict:
    response = client.post(
        f"/api/v1/friends/requests/{request_id}/accept",
        headers=receiver["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def make_friends(user_a: dict | None = None, user_b: dict | None = None) -> tuple[dict, dict]:
    first = user_a or register_user()
    second = user_b or register_user()
    request = send_request(first, second)
    accept_request(second, request["id"])
    return first, second


def create_direct_conversation(user: dict, other: dict) -> dict:
    response = client.post(
        "/api/v1/conversations/direct",
        headers=user["headers"],
        json={"user_id": other["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def send_message(user: dict, conversation_id: str, body: str = "Hello from ChessJU") -> dict:
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=user["headers"],
        json={"body": body},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_user_can_send_friend_request() -> None:
    sender = register_user()
    receiver = register_user()

    response = client.post(
        "/api/v1/friends/requests",
        headers=sender["headers"],
        json={"receiver_id": receiver["id"]},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["sender"]["id"] == sender["id"]
    assert response.json()["receiver"]["id"] == receiver["id"]


def test_unauthenticated_user_cannot_send_friend_request() -> None:
    receiver = register_user()

    response = client.post("/api/v1/friends/requests", json={"receiver_id": receiver["id"]})

    assert response.status_code == 401


def test_cannot_send_friend_request_to_self() -> None:
    user = register_user()

    response = client.post(
        "/api/v1/friends/requests",
        headers=user["headers"],
        json={"receiver_id": user["id"]},
    )

    assert response.status_code == 422


def test_duplicate_pending_friend_request_rejected() -> None:
    sender = register_user()
    receiver = register_user()
    send_request(sender, receiver)

    response = client.post(
        "/api/v1/friends/requests",
        headers=sender["headers"],
        json={"receiver_id": receiver["id"]},
    )

    assert response.status_code == 409


def test_receiver_can_accept_request_and_friendship_is_created() -> None:
    sender = register_user()
    receiver = register_user()
    friend_request = send_request(sender, receiver)

    response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/accept",
        headers=receiver["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    friends_response = client.get("/api/v1/friends", headers=sender["headers"])
    assert friends_response.status_code == 200
    assert friends_response.json()["total"] == 1
    assert friends_response.json()["items"][0]["id"] == receiver["id"]


def test_receiver_can_reject_request() -> None:
    sender = register_user()
    receiver = register_user()
    friend_request = send_request(sender, receiver)

    response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/reject",
        headers=receiver["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_sender_can_cancel_request() -> None:
    sender = register_user()
    receiver = register_user()
    friend_request = send_request(sender, receiver)

    response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/cancel",
        headers=sender["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_non_sender_cannot_cancel_request() -> None:
    sender = register_user()
    receiver = register_user()
    other = register_user()
    friend_request = send_request(sender, receiver)

    response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/cancel",
        headers=other["headers"],
    )

    assert response.status_code == 403


def test_non_receiver_cannot_accept_or_reject_request() -> None:
    sender = register_user()
    receiver = register_user()
    other = register_user()
    friend_request = send_request(sender, receiver)

    accept_response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/accept",
        headers=other["headers"],
    )
    reject_response = client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/reject",
        headers=other["headers"],
    )

    assert accept_response.status_code == 403
    assert reject_response.status_code == 403


def test_user_can_list_and_remove_friends() -> None:
    user, friend = make_friends()

    list_response = client.get("/api/v1/friends", headers=user["headers"])
    delete_response = client.delete(f"/api/v1/friends/{friend['id']}", headers=user["headers"])
    second_list_response = client.get("/api/v1/friends", headers=user["headers"])

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert delete_response.status_code == 200
    assert delete_response.json()["removed"] is True
    assert second_list_response.json()["total"] == 0


def test_friendship_stored_in_normalized_order() -> None:
    user, friend = make_friends()

    async def load_friendship() -> Friendship:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Friendship).where(
                    (Friendship.user_a_id == uuid.UUID(user["id"]))
                    | (Friendship.user_b_id == uuid.UUID(user["id"]))
                )
            )
            return result.scalar_one()

    friendship = asyncio.run(load_friendship())

    assert friendship.user_a_id.hex < friendship.user_b_id.hex


def test_existing_friendship_blocks_duplicate_request() -> None:
    user, friend = make_friends()

    response = client.post(
        "/api/v1/friends/requests",
        headers=user["headers"],
        json={"receiver_id": friend["id"]},
    )

    assert response.status_code == 409


def test_user_can_block_and_unblock_another_user() -> None:
    user = register_user()
    other = register_user()

    block_response = client.post(
        "/api/v1/blocks",
        headers=user["headers"],
        json={"blocked_id": other["id"]},
    )
    list_response = client.get("/api/v1/blocks", headers=user["headers"])
    unblock_response = client.delete(f"/api/v1/blocks/{other['id']}", headers=user["headers"])

    assert block_response.status_code == 201
    assert list_response.json()["total"] == 1
    assert unblock_response.json()["unblocked"] is True


def test_cannot_block_self() -> None:
    user = register_user()

    response = client.post(
        "/api/v1/blocks",
        headers=user["headers"],
        json={"blocked_id": user["id"]},
    )

    assert response.status_code == 422


def test_blocking_cancels_pending_requests() -> None:
    sender = register_user()
    receiver = register_user()
    friend_request = send_request(sender, receiver)

    block_response = client.post(
        "/api/v1/blocks",
        headers=receiver["headers"],
        json={"blocked_id": sender["id"]},
    )

    async def load_request_status() -> str:
        async with AsyncSessionLocal() as session:
            request = await session.get(FriendRequest, uuid.UUID(friend_request["id"]))
            assert request is not None
            return request.status

    assert block_response.status_code == 201
    assert asyncio.run(load_request_status()) == "cancelled"


def test_blocking_removes_friendship() -> None:
    user, friend = make_friends()

    response = client.post(
        "/api/v1/blocks",
        headers=user["headers"],
        json={"blocked_id": friend["id"]},
    )
    list_response = client.get("/api/v1/friends", headers=user["headers"])

    assert response.status_code == 201
    assert list_response.json()["total"] == 0


def test_blocked_user_cannot_send_friend_request() -> None:
    blocker = register_user()
    blocked = register_user()
    client.post(
        "/api/v1/blocks",
        headers=blocker["headers"],
        json={"blocked_id": blocked["id"]},
    )

    response = client.post(
        "/api/v1/friends/requests",
        headers=blocked["headers"],
        json={"receiver_id": blocker["id"]},
    )

    assert response.status_code == 403


def test_friends_can_create_direct_conversation() -> None:
    user, friend = make_friends()

    response = client.post(
        "/api/v1/conversations/direct",
        headers=user["headers"],
        json={"user_id": friend["id"]},
    )

    assert response.status_code == 201
    assert response.json()["type"] == "direct"
    assert len(response.json()["members"]) == 2


def test_non_friends_cannot_create_direct_conversation() -> None:
    user = register_user()
    other = register_user()

    response = client.post(
        "/api/v1/conversations/direct",
        headers=user["headers"],
        json={"user_id": other["id"]},
    )

    assert response.status_code == 403


def test_blocked_users_cannot_create_direct_conversation() -> None:
    user, friend = make_friends()
    client.post(
        "/api/v1/blocks",
        headers=user["headers"],
        json={"blocked_id": friend["id"]},
    )

    response = client.post(
        "/api/v1/conversations/direct",
        headers=friend["headers"],
        json={"user_id": user["id"]},
    )

    assert response.status_code == 403


def test_existing_direct_conversation_is_reused() -> None:
    user, friend = make_friends()

    first = create_direct_conversation(user, friend)
    second = create_direct_conversation(user, friend)

    assert second["id"] == first["id"]


def test_only_members_can_view_conversation() -> None:
    user, friend = make_friends()
    other = register_user()
    conversation = create_direct_conversation(user, friend)

    member_response = client.get(
        f"/api/v1/conversations/{conversation['id']}",
        headers=user["headers"],
    )
    other_response = client.get(
        f"/api/v1/conversations/{conversation['id']}",
        headers=other["headers"],
    )

    assert member_response.status_code == 200
    assert other_response.status_code == 403


def test_member_can_send_message() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=user["headers"],
        json={"body": "First message"},
    )

    assert response.status_code == 200
    assert response.json()["body"] == "First message"


def test_non_member_cannot_send_message() -> None:
    user, friend = make_friends()
    other = register_user()
    conversation = create_direct_conversation(user, friend)

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=other["headers"],
        json={"body": "No access"},
    )

    assert response.status_code == 403


def test_empty_and_overlong_messages_are_rejected() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)

    empty_response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=user["headers"],
        json={"body": "   "},
    )
    overlong_response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=user["headers"],
        json={"body": "x" * 2001},
    )

    assert empty_response.status_code == 422
    assert overlong_response.status_code == 422


def test_members_can_list_messages_ordered_oldest_first() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)
    first = send_message(user, conversation["id"], "First")
    second = send_message(friend, conversation["id"], "Second")

    response = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=user["headers"],
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [first["id"], second["id"]]


def test_sender_can_soft_delete_own_message_and_body_is_sanitized() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)
    message = send_message(user, conversation["id"], "Delete me")

    delete_response = client.delete(f"/api/v1/messages/{message['id']}", headers=user["headers"])
    list_response = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=friend["headers"],
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert list_response.json()["items"][0]["body"] is None
    assert list_response.json()["items"][0]["deleted_at"] is not None


def test_non_sender_cannot_delete_message() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)
    message = send_message(user, conversation["id"], "Keep me")
    other = register_user()

    response = client.delete(f"/api/v1/messages/{message['id']}", headers=other["headers"])

    assert response.status_code == 403


def test_user_can_mark_conversation_as_read() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)
    send_message(friend, conversation["id"], "Please read")

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/read",
        headers=user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["read_count"] == 1


def test_non_member_cannot_mark_conversation_as_read() -> None:
    user, friend = make_friends()
    other = register_user()
    conversation = create_direct_conversation(user, friend)

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/read",
        headers=other["headers"],
    )

    assert response.status_code == 403


def test_admin_can_list_conversations_and_messages() -> None:
    user, friend = make_friends()
    admin = register_admin()
    conversation = create_direct_conversation(user, friend)
    send_message(user, conversation["id"], "Admin visible")

    conversations_response = client.get(
        "/api/v1/admin/chat/conversations",
        headers=admin["headers"],
    )
    messages_response = client.get(
        "/api/v1/admin/chat/messages",
        headers=admin["headers"],
        params={"conversation_id": conversation["id"]},
    )

    assert conversations_response.status_code == 200
    assert messages_response.status_code == 200
    assert messages_response.json()["total"] >= 1


def test_member_cannot_access_admin_chat_endpoints() -> None:
    user = register_user()

    conversations_response = client.get(
        "/api/v1/admin/chat/conversations",
        headers=user["headers"],
    )
    messages_response = client.get("/api/v1/admin/chat/messages", headers=user["headers"])

    assert conversations_response.status_code == 403
    assert messages_response.status_code == 403


def test_admin_can_list_friend_requests_and_friendships() -> None:
    user, friend = make_friends()
    admin = register_admin()
    _ = user, friend

    requests_response = client.get(
        "/api/v1/admin/social/friend-requests",
        headers=admin["headers"],
    )
    friendships_response = client.get(
        "/api/v1/admin/social/friendships",
        headers=admin["headers"],
    )

    assert requests_response.status_code == 200
    assert friendships_response.status_code == 200
    assert requests_response.json()["total"] >= 1
    assert friendships_response.json()["total"] >= 1


def test_admin_delete_message_creates_audit_log() -> None:
    user, friend = make_friends()
    admin = register_admin()
    conversation = create_direct_conversation(user, friend)
    message = send_message(user, conversation["id"], "Moderate me")

    response = client.delete(f"/api/v1/messages/{message['id']}", headers=admin["headers"])

    async def audit_exists() -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AdminActionLog).where(
                    AdminActionLog.action == "message.admin_deleted",
                    AdminActionLog.entity_id == uuid.UUID(message["id"]),
                )
            )
            return result.scalar_one_or_none() is not None

    assert response.status_code == 200
    assert asyncio.run(audit_exists()) is True


def test_imported_message_row_is_soft_deleted_not_removed() -> None:
    user, friend = make_friends()
    conversation = create_direct_conversation(user, friend)
    message = send_message(user, conversation["id"], "Still stored")

    client.delete(f"/api/v1/messages/{message['id']}", headers=user["headers"])

    async def load_message() -> Message:
        async with AsyncSessionLocal() as session:
            record = await session.get(Message, uuid.UUID(message["id"]))
            assert record is not None
            return record

    record = asyncio.run(load_message())

    assert record.deleted_at is not None
    assert record.body == "Still stored"
