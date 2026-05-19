import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.admin.services import create_admin_action_log
from app.auth.constants import ADMIN_ROLE_NAMES
from app.common.time import utc_now
from app.notifications.services import create_user_notification
from app.social.models import (
    BlockedUser,
    Conversation,
    ConversationMember,
    FriendRequest,
    Friendship,
    Message,
    MessageRead,
)
from app.social.schemas import (
    BlockCreateRequest,
    BlockListResponse,
    BlockResponse,
    ConversationListResponse,
    ConversationResponse,
    DeleteMessageResponse,
    DirectConversationCreateRequest,
    FriendListResponse,
    FriendRequestCreateRequest,
    FriendRequestListResponse,
    FriendRequestResponse,
    FriendResponse,
    MarkReadResponse,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    RemoveFriendResponse,
    SocialUserSummary,
    UnblockResponse,
)
from app.users.models import User
from app.users.services import get_role_names_for_user

PENDING_REQUEST_STATUS = "pending"
TERMINAL_REQUEST_STATUSES = {"accepted", "rejected", "cancelled"}


def _normalize_friend_pair(
    user_id: uuid.UUID, other_user_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    first, second = sorted((user_id, other_user_id), key=lambda value: value.hex)
    return first, second


def _user_summary(user: User) -> SocialUserSummary:
    return SocialUserSummary(
        id=user.id,
        username=user.profile.username,
        full_name=user.profile.full_name,
        avatar_file_id=user.profile.avatar_file_id,
    )


async def _is_admin(session: AsyncSession, user_id: uuid.UUID) -> bool:
    roles = set(await get_role_names_for_user(session, user_id))
    return bool(roles.intersection(ADMIN_ROLE_NAMES))


async def _get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None), User.status == "active")
        .options(selectinload(User.profile))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _get_friend_request(
    session: AsyncSession, request_id: uuid.UUID
) -> FriendRequest:
    record = await session.get(FriendRequest, request_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found",
        )
    return record


async def _get_friendship(
    session: AsyncSession, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Friendship | None:
    user_a_id, user_b_id = _normalize_friend_pair(user_id, other_user_id)
    result = await session.execute(
        select(Friendship).where(
            Friendship.user_a_id == user_a_id,
            Friendship.user_b_id == user_b_id,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_friendship(
    session: AsyncSession, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Friendship:
    friendship = await _get_friendship(session, user_id, other_user_id)
    if friendship is not None:
        return friendship

    user_a_id, user_b_id = _normalize_friend_pair(user_id, other_user_id)
    friendship = Friendship(user_a_id=user_a_id, user_b_id=user_b_id)
    session.add(friendship)
    await session.flush()
    return friendship


async def _is_blocked_between(
    session: AsyncSession, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(BlockedUser.id).where(
            or_(
                and_(BlockedUser.blocker_id == user_id, BlockedUser.blocked_id == other_user_id),
                and_(BlockedUser.blocker_id == other_user_id, BlockedUser.blocked_id == user_id),
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def _get_block(
    session: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
) -> BlockedUser | None:
    result = await session.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == blocker_id,
            BlockedUser.blocked_id == blocked_id,
        )
    )
    return result.scalar_one_or_none()


async def _friend_request_response(
    session: AsyncSession, friend_request: FriendRequest
) -> FriendRequestResponse:
    sender = await _get_user(session, friend_request.sender_id)
    receiver = await _get_user(session, friend_request.receiver_id)
    return FriendRequestResponse(
        id=friend_request.id,
        sender=_user_summary(sender),
        receiver=_user_summary(receiver),
        status=friend_request.status,
        created_at=friend_request.created_at,
        responded_at=friend_request.responded_at,
    )


async def send_friend_request(
    session: AsyncSession,
    user: User,
    payload: FriendRequestCreateRequest,
) -> FriendRequestResponse:
    if payload.receiver_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot send a friend request to yourself",
        )

    await _get_user(session, payload.receiver_id)

    if await _is_blocked_between(session, user.id, payload.receiver_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")

    if await _get_friendship(session, user.id, payload.receiver_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Friendship already exists",
        )

    existing_result = await session.execute(
        select(FriendRequest).where(
            FriendRequest.sender_id == user.id,
            FriendRequest.receiver_id == payload.receiver_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    now = utc_now()
    if existing is not None:
        if existing.status == PENDING_REQUEST_STATUS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Friend request already pending",
            )
        if existing.status in TERMINAL_REQUEST_STATUSES:
            existing.status = PENDING_REQUEST_STATUS
            existing.created_at = now
            existing.responded_at = None
            await session.flush()
            await create_user_notification(
                session,
                user_id=payload.receiver_id,
                notification_type="friend_request.received",
                title="New friend request",
                body="You have a new friend request",
                data={"friend_request_id": existing.id, "sender_id": user.id},
            )
            await session.commit()
            await session.refresh(existing)
            return await _friend_request_response(session, existing)

    opposite_result = await session.execute(
        select(FriendRequest).where(
            FriendRequest.sender_id == payload.receiver_id,
            FriendRequest.receiver_id == user.id,
            FriendRequest.status == PENDING_REQUEST_STATUS,
        )
    )
    opposite = opposite_result.scalar_one_or_none()
    if opposite is not None:
        opposite.status = "accepted"
        opposite.responded_at = now
        await _ensure_friendship(session, user.id, payload.receiver_id)
        await create_user_notification(
            session,
            user_id=payload.receiver_id,
            notification_type="friend_request.accepted",
            title="Friend request accepted",
            body="Your friend request was accepted",
            data={"friend_request_id": opposite.id, "friend_id": user.id},
        )
        await session.commit()
        await session.refresh(opposite)
        return await _friend_request_response(session, opposite)

    friend_request = FriendRequest(sender_id=user.id, receiver_id=payload.receiver_id)
    session.add(friend_request)
    try:
        await session.flush()
        await create_user_notification(
            session,
            user_id=payload.receiver_id,
            notification_type="friend_request.received",
            title="New friend request",
            body="You have a new friend request",
            data={"friend_request_id": friend_request.id, "sender_id": user.id},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Friend request already exists",
        ) from exc
    await session.refresh(friend_request)
    return await _friend_request_response(session, friend_request)


def _filter_friend_requests(
    statement: Select[tuple[FriendRequest]],
    user_id: uuid.UUID,
    direction: str | None,
    status_filter: str | None,
) -> Select[tuple[FriendRequest]]:
    if direction == "incoming":
        statement = statement.where(FriendRequest.receiver_id == user_id)
    elif direction == "outgoing":
        statement = statement.where(FriendRequest.sender_id == user_id)
    else:
        statement = statement.where(
            or_(FriendRequest.sender_id == user_id, FriendRequest.receiver_id == user_id)
        )
    if status_filter is not None:
        statement = statement.where(FriendRequest.status == status_filter)
    return statement


async def list_friend_requests(
    session: AsyncSession,
    user: User,
    direction: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> FriendRequestListResponse:
    if direction not in {None, "incoming", "outgoing"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid direction",
        )
    if status_filter not in {None, "pending", "accepted", "rejected", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid status",
        )

    total_statement = _filter_friend_requests(
        select(func.count()).select_from(FriendRequest),
        user.id,
        direction,
        status_filter,
    )
    total = await session.scalar(total_statement)
    result = await session.execute(
        _filter_friend_requests(select(FriendRequest), user.id, direction, status_filter)
        .order_by(FriendRequest.created_at.desc(), FriendRequest.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _friend_request_response(session, item) for item in result.scalars()]
    return FriendRequestListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def accept_friend_request(
    session: AsyncSession, user: User, request_id: uuid.UUID
) -> FriendRequestResponse:
    friend_request = await _get_friend_request(session, request_id)
    if friend_request.receiver_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only receiver can accept",
        )
    if friend_request.status != PENDING_REQUEST_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Friend request is not pending",
        )
    if await _is_blocked_between(session, friend_request.sender_id, friend_request.receiver_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")

    friend_request.status = "accepted"
    friend_request.responded_at = utc_now()
    await _ensure_friendship(session, friend_request.sender_id, friend_request.receiver_id)
    await create_user_notification(
        session,
        user_id=friend_request.sender_id,
        notification_type="friend_request.accepted",
        title="Friend request accepted",
        body="Your friend request was accepted",
        data={"friend_request_id": friend_request.id, "friend_id": user.id},
    )
    await session.commit()
    await session.refresh(friend_request)
    return await _friend_request_response(session, friend_request)


async def reject_friend_request(
    session: AsyncSession, user: User, request_id: uuid.UUID
) -> FriendRequestResponse:
    friend_request = await _get_friend_request(session, request_id)
    if friend_request.receiver_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only receiver can reject",
        )
    if friend_request.status != PENDING_REQUEST_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Friend request is not pending",
        )

    friend_request.status = "rejected"
    friend_request.responded_at = utc_now()
    await session.commit()
    await session.refresh(friend_request)
    return await _friend_request_response(session, friend_request)


async def cancel_friend_request(
    session: AsyncSession, user: User, request_id: uuid.UUID
) -> FriendRequestResponse:
    friend_request = await _get_friend_request(session, request_id)
    if friend_request.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only sender can cancel")
    if friend_request.status != PENDING_REQUEST_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Friend request is not pending",
        )

    friend_request.status = "cancelled"
    friend_request.responded_at = utc_now()
    await session.commit()
    await session.refresh(friend_request)
    return await _friend_request_response(session, friend_request)


async def _friend_response(
    session: AsyncSession, friendship: Friendship, current_user_id: uuid.UUID
) -> FriendResponse:
    friend_id = (
        friendship.user_b_id
        if friendship.user_a_id == current_user_id
        else friendship.user_a_id
    )
    friend = await _get_user(session, friend_id)
    return FriendResponse(
        friendship_id=friendship.id,
        id=friend.id,
        username=friend.profile.username,
        full_name=friend.profile.full_name,
        avatar_file_id=friend.profile.avatar_file_id,
        created_at=friendship.created_at,
    )


async def list_friends(
    session: AsyncSession, user: User, limit: int = 50, offset: int = 0
) -> FriendListResponse:
    where_clause = or_(Friendship.user_a_id == user.id, Friendship.user_b_id == user.id)
    total = await session.scalar(select(func.count()).select_from(Friendship).where(where_clause))
    result = await session.execute(
        select(Friendship)
        .where(where_clause)
        .order_by(Friendship.created_at.desc(), Friendship.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _friend_response(session, item, user.id) for item in result.scalars()]
    return FriendListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def remove_friendship(
    session: AsyncSession, user: User, other_user_id: uuid.UUID
) -> RemoveFriendResponse:
    friendship = await _get_friendship(session, user.id, other_user_id)
    if friendship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friendship not found")
    await session.delete(friendship)
    await session.commit()
    return RemoveFriendResponse(removed=True)


async def block_user(
    session: AsyncSession, user: User, payload: BlockCreateRequest
) -> BlockResponse:
    if payload.blocked_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot block yourself",
        )

    blocked_user = await _get_user(session, payload.blocked_id)
    existing = await _get_block(session, user.id, payload.blocked_id)
    if existing is not None:
        return BlockResponse(
            id=existing.id,
            blocked_user=_user_summary(blocked_user),
            created_at=existing.created_at,
        )

    record = BlockedUser(blocker_id=user.id, blocked_id=payload.blocked_id)
    session.add(record)
    await session.execute(
        update(FriendRequest)
        .where(
            FriendRequest.status == PENDING_REQUEST_STATUS,
            or_(
                and_(
                    FriendRequest.sender_id == user.id,
                    FriendRequest.receiver_id == payload.blocked_id,
                ),
                and_(
                    FriendRequest.sender_id == payload.blocked_id,
                    FriendRequest.receiver_id == user.id,
                ),
            ),
        )
        .values(status="cancelled", responded_at=utc_now())
    )
    friendship = await _get_friendship(session, user.id, payload.blocked_id)
    if friendship is not None:
        await session.delete(friendship)

    await session.commit()
    await session.refresh(record)
    return BlockResponse(
        id=record.id,
        blocked_user=_user_summary(blocked_user),
        created_at=record.created_at,
    )


async def list_blocks(
    session: AsyncSession, user: User, limit: int = 50, offset: int = 0
) -> BlockListResponse:
    total = await session.scalar(
        select(func.count()).select_from(BlockedUser).where(BlockedUser.blocker_id == user.id)
    )
    result = await session.execute(
        select(BlockedUser)
        .where(BlockedUser.blocker_id == user.id)
        .order_by(BlockedUser.created_at.desc(), BlockedUser.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items: list[BlockResponse] = []
    for block in result.scalars():
        blocked_user = await _get_user(session, block.blocked_id)
        items.append(
            BlockResponse(
                id=block.id,
                blocked_user=_user_summary(blocked_user),
                created_at=block.created_at,
            )
        )
    return BlockListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def unblock_user(
    session: AsyncSession, user: User, blocked_id: uuid.UUID
) -> UnblockResponse:
    result = await session.execute(
        delete(BlockedUser).where(
            BlockedUser.blocker_id == user.id,
            BlockedUser.blocked_id == blocked_id,
        )
    )
    await session.commit()
    return UnblockResponse(unblocked=(result.rowcount or 0) > 0)


async def _get_conversation(session: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


async def _is_conversation_member(
    session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(ConversationMember.conversation_id).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
            ConversationMember.left_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def _require_conversation_member(
    session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    if not await _is_conversation_member(session, conversation_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation access denied",
        )


async def _direct_conversation_between(
    session: AsyncSession, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Conversation | None:
    member_a = aliased(ConversationMember)
    member_b = aliased(ConversationMember)
    result = await session.execute(
        select(Conversation)
        .join(member_a, member_a.conversation_id == Conversation.id)
        .join(member_b, member_b.conversation_id == Conversation.id)
        .where(
            Conversation.type == "direct",
            member_a.user_id == user_id,
            member_a.left_at.is_(None),
            member_b.user_id == other_user_id,
            member_b.left_at.is_(None),
        )
        .order_by(Conversation.created_at.asc())
    )
    return result.scalars().first()


async def _message_response(session: AsyncSession, message: Message) -> MessageResponse:
    sender = await _get_user(session, message.sender_id)
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender=_user_summary(sender),
        body=None if message.deleted_at is not None else message.body,
        message_type=message.message_type,
        created_at=message.created_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
    )


async def _conversation_response(
    session: AsyncSession, conversation: Conversation
) -> ConversationResponse:
    member_result = await session.execute(
        select(ConversationMember)
        .where(ConversationMember.conversation_id == conversation.id)
        .order_by(ConversationMember.joined_at.asc())
    )
    members = []
    for member in member_result.scalars():
        member_user = await _get_user(session, member.user_id)
        members.append(
            {
                "user": _user_summary(member_user),
                "role": member.role,
                "joined_at": member.joined_at,
                "left_at": member.left_at,
            }
        )

    last_message_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )
    last_message = last_message_result.scalar_one_or_none()
    return ConversationResponse(
        id=conversation.id,
        type=conversation.type,
        members=members,
        last_message=await _message_response(session, last_message) if last_message else None,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def create_or_get_direct_conversation(
    session: AsyncSession,
    user: User,
    payload: DirectConversationCreateRequest,
) -> ConversationResponse:
    if payload.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot create direct conversation with yourself",
        )
    await _get_user(session, payload.user_id)
    if await _is_blocked_between(session, user.id, payload.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
    if await _get_friendship(session, user.id, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Users are not friends")

    existing = await _direct_conversation_between(session, user.id, payload.user_id)
    if existing is not None:
        return await _conversation_response(session, existing)

    conversation = Conversation(type="direct")
    session.add(conversation)
    await session.flush()
    session.add_all(
        [
            ConversationMember(conversation_id=conversation.id, user_id=user.id),
            ConversationMember(conversation_id=conversation.id, user_id=payload.user_id),
        ]
    )
    await session.commit()
    await session.refresh(conversation)
    return await _conversation_response(session, conversation)


async def list_conversations(
    session: AsyncSession, user: User, limit: int = 50, offset: int = 0
) -> ConversationListResponse:
    member_filter = (
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == user.id, ConversationMember.left_at.is_(None))
        .subquery()
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.id.in_(select(member_filter.c.conversation_id)))
    )
    result = await session.execute(
        select(Conversation)
        .where(Conversation.id.in_(select(member_filter.c.conversation_id)))
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _conversation_response(session, item) for item in result.scalars()]
    return ConversationListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def get_conversation_detail(
    session: AsyncSession, user: User, conversation_id: uuid.UUID
) -> ConversationResponse:
    await _require_conversation_member(session, conversation_id, user.id)
    conversation = await _get_conversation(session, conversation_id)
    return await _conversation_response(session, conversation)


async def list_messages(
    session: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> MessageListResponse:
    await _require_conversation_member(session, conversation_id, user.id)
    total = await session.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _message_response(session, item) for item in result.scalars()]
    return MessageListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def send_message(
    session: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
) -> MessageResponse:
    await _require_conversation_member(session, conversation_id, user.id)
    conversation = await _get_conversation(session, conversation_id)
    member_result = await session.execute(
        select(ConversationMember.user_id).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.left_at.is_(None),
            ConversationMember.user_id != user.id,
        )
    )
    other_member_ids = list(member_result.scalars().all())
    for other_user_id in other_member_ids:
        if await _is_blocked_between(session, user.id, other_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")

    message = Message(conversation_id=conversation_id, sender_id=user.id, body=payload.body)
    conversation.updated_at = utc_now()
    session.add(message)
    await session.flush()
    for other_user_id in other_member_ids:
        await create_user_notification(
            session,
            user_id=other_user_id,
            notification_type="message.received",
            title="New message",
            body="You have a new message",
            data={
                "conversation_id": conversation_id,
                "message_id": message.id,
                "sender_id": user.id,
            },
        )
    await session.commit()
    await session.refresh(message)
    return await _message_response(session, message)


async def mark_conversation_read(
    session: AsyncSession, user: User, conversation_id: uuid.UUID
) -> MarkReadResponse:
    await _require_conversation_member(session, conversation_id, user.id)
    read_at = utc_now()
    message_result = await session.execute(
        select(Message.id).where(Message.conversation_id == conversation_id)
    )
    message_ids = list(message_result.scalars().all())
    existing_result = await session.execute(
        select(MessageRead.message_id).where(
            MessageRead.user_id == user.id,
            MessageRead.message_id.in_(message_ids) if message_ids else False,
        )
    )
    existing_ids = set(existing_result.scalars().all())
    read_count = 0
    for message_id in message_ids:
        if message_id in existing_ids:
            read_record = await session.get(
                MessageRead,
                {"message_id": message_id, "user_id": user.id},
            )
            if read_record is not None:
                read_record.read_at = read_at
        else:
            session.add(MessageRead(message_id=message_id, user_id=user.id, read_at=read_at))
        read_count += 1
    await session.commit()
    return MarkReadResponse(conversation_id=conversation_id, read_count=read_count, read_at=read_at)


async def _get_message(session: AsyncSession, message_id: uuid.UUID) -> Message:
    message = await session.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message


def _message_audit_snapshot(message: Message) -> dict[str, str | None]:
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id),
        "message_type": message.message_type,
        "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
    }


async def delete_message(
    session: AsyncSession,
    user: User,
    message_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DeleteMessageResponse:
    message = await _get_message(session, message_id)
    is_admin = await _is_admin(session, user.id)
    if message.sender_id != user.id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only sender can delete")
    if message.sender_id == user.id:
        await _require_conversation_member(session, message.conversation_id, user.id)

    before = _message_audit_snapshot(message)
    if message.deleted_at is None:
        message.deleted_at = utc_now()
    if is_admin and message.sender_id != user.id:
        await create_admin_action_log(
            db=session,
            admin_id=user.id,
            action="message.admin_deleted",
            entity_type="message",
            entity_id=message.id,
            before=before,
            after=_message_audit_snapshot(message),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    await session.commit()
    return DeleteMessageResponse(id=message.id, deleted=True, deleted_at=message.deleted_at)


async def list_admin_friend_requests(
    session: AsyncSession,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> FriendRequestListResponse:
    statement = select(FriendRequest)
    count_statement = select(func.count()).select_from(FriendRequest)
    if status_filter is not None:
        statement = statement.where(FriendRequest.status == status_filter)
        count_statement = count_statement.where(FriendRequest.status == status_filter)
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(FriendRequest.created_at.desc(), FriendRequest.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _friend_request_response(session, item) for item in result.scalars()]
    return FriendRequestListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def list_admin_friendships(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> FriendListResponse:
    total = await session.scalar(select(func.count()).select_from(Friendship))
    result = await session.execute(
        select(Friendship)
        .order_by(Friendship.created_at.desc(), Friendship.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items: list[FriendResponse] = []
    for friendship in result.scalars():
        friend = await _get_user(session, friendship.user_b_id)
        items.append(
            FriendResponse(
                friendship_id=friendship.id,
                id=friend.id,
                username=friend.profile.username,
                full_name=friend.profile.full_name,
                avatar_file_id=friend.profile.avatar_file_id,
                created_at=friendship.created_at,
            )
        )
    return FriendListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def list_admin_conversations(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> ConversationListResponse:
    total = await session.scalar(select(func.count()).select_from(Conversation))
    result = await session.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [await _conversation_response(session, item) for item in result.scalars()]
    return ConversationListResponse(items=items, limit=limit, offset=offset, total=total or 0)


async def list_admin_messages(
    session: AsyncSession,
    conversation_id: uuid.UUID | None = None,
    sender_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> MessageListResponse:
    statement = select(Message)
    count_statement = select(func.count()).select_from(Message)
    if conversation_id is not None:
        statement = statement.where(Message.conversation_id == conversation_id)
        count_statement = count_statement.where(Message.conversation_id == conversation_id)
    if sender_id is not None:
        statement = statement.where(Message.sender_id == sender_id)
        count_statement = count_statement.where(Message.sender_id == sender_id)
    total = await session.scalar(count_statement)
    result = await session.execute(
        statement.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit).offset(offset)
    )
    items = [await _message_response(session, item) for item in result.scalars()]
    return MessageListResponse(items=items, limit=limit, offset=offset, total=total or 0)
