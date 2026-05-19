import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.common.rate_limit import enforce_user_rate_limit
from app.config import get_settings
from app.database import get_db_session
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
    MarkReadResponse,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    RemoveFriendResponse,
    UnblockResponse,
)
from app.social.services import (
    accept_friend_request,
    block_user,
    cancel_friend_request,
    create_or_get_direct_conversation,
    delete_message,
    get_conversation_detail,
    list_admin_conversations,
    list_admin_friend_requests,
    list_admin_friendships,
    list_admin_messages,
    list_blocks,
    list_conversations,
    list_friend_requests,
    list_friends,
    list_messages,
    mark_conversation_read,
    reject_friend_request,
    remove_friendship,
    send_friend_request,
    send_message,
    unblock_user,
)
from app.users.models import User

router = APIRouter(tags=["Social/Chat"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/friends/requests",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_friend_request(
    payload: FriendRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    return await send_friend_request(session=session, user=current_user, payload=payload)


@router.get("/friends/requests", response_model=FriendRequestListResponse)
async def my_friend_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    direction: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FriendRequestListResponse:
    return await list_friend_requests(
        session=session,
        user=current_user,
        direction=direction,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/friends/requests/{request_id}/accept", response_model=FriendRequestResponse)
async def accept_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    return await accept_friend_request(session=session, user=current_user, request_id=request_id)


@router.post("/friends/requests/{request_id}/reject", response_model=FriendRequestResponse)
async def reject_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    return await reject_friend_request(session=session, user=current_user, request_id=request_id)


@router.post("/friends/requests/{request_id}/cancel", response_model=FriendRequestResponse)
async def cancel_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FriendRequestResponse:
    return await cancel_friend_request(session=session, user=current_user, request_id=request_id)


@router.get("/friends", response_model=FriendListResponse)
async def my_friends(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FriendListResponse:
    return await list_friends(session=session, user=current_user, limit=limit, offset=offset)


@router.delete("/friends/{user_id}", response_model=RemoveFriendResponse)
async def delete_friend(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> RemoveFriendResponse:
    return await remove_friendship(session=session, user=current_user, other_user_id=user_id)


@router.post("/blocks", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(
    payload: BlockCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BlockResponse:
    return await block_user(session=session, user=current_user, payload=payload)


@router.get("/blocks", response_model=BlockListResponse)
async def my_blocks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> BlockListResponse:
    return await list_blocks(session=session, user=current_user, limit=limit, offset=offset)


@router.delete("/blocks/{blocked_id}", response_model=UnblockResponse)
async def delete_block(
    blocked_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UnblockResponse:
    return await unblock_user(session=session, user=current_user, blocked_id=blocked_id)


@router.post(
    "/conversations/direct",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_direct_conversation(
    payload: DirectConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    return await create_or_get_direct_conversation(
        session=session,
        user=current_user,
        payload=payload,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def my_conversations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ConversationListResponse:
    return await list_conversations(session=session, user=current_user, limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def conversation_detail(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    return await get_conversation_detail(
        session=session,
        user=current_user,
        conversation_id=conversation_id,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MessageListResponse:
    return await list_messages(
        session=session,
        user=current_user,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    settings = get_settings()
    await enforce_user_rate_limit(
        request,
        user=current_user,
        scope="message",
        limit=settings.rate_limit_message_per_minute,
        window_seconds=60,
    )
    return await send_message(
        session=session,
        user=current_user,
        conversation_id=conversation_id,
        payload=payload,
    )


@router.post("/conversations/{conversation_id}/read", response_model=MarkReadResponse)
async def mark_read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MarkReadResponse:
    return await mark_conversation_read(
        session=session,
        user=current_user,
        conversation_id=conversation_id,
    )


@router.delete("/messages/{message_id}", response_model=DeleteMessageResponse)
async def remove_message(
    message_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DeleteMessageResponse:
    return await delete_message(
        session=session,
        user=current_user,
        message_id=message_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/admin/social/friend-requests", response_model=FriendRequestListResponse)
async def admin_friend_requests(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FriendRequestListResponse:
    _ = current_admin
    return await list_admin_friend_requests(
        session=session,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/social/friendships", response_model=FriendListResponse)
async def admin_friendships(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FriendListResponse:
    _ = current_admin
    return await list_admin_friendships(session=session, limit=limit, offset=offset)


@router.get("/admin/chat/conversations", response_model=ConversationListResponse)
async def admin_conversations(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ConversationListResponse:
    _ = current_admin
    return await list_admin_conversations(session=session, limit=limit, offset=offset)


@router.get("/admin/chat/messages", response_model=MessageListResponse)
async def admin_messages(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    conversation_id: uuid.UUID | None = None,
    sender_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MessageListResponse:
    _ = current_admin
    return await list_admin_messages(
        session=session,
        conversation_id=conversation_id,
        sender_id=sender_id,
        limit=limit,
        offset=offset,
    )
