import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FriendRequestStatus = Literal["pending", "accepted", "rejected", "cancelled"]
FriendRequestDirection = Literal["incoming", "outgoing"]


class SocialUserSummary(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    avatar_file_id: uuid.UUID | None = None


class FriendRequestCreateRequest(BaseModel):
    receiver_id: uuid.UUID


class FriendRequestResponse(BaseModel):
    id: uuid.UUID
    sender: SocialUserSummary
    receiver: SocialUserSummary
    status: str
    created_at: datetime
    responded_at: datetime | None


class FriendRequestListResponse(BaseModel):
    items: list[FriendRequestResponse]
    limit: int
    offset: int
    total: int


class FriendResponse(SocialUserSummary):
    friendship_id: uuid.UUID
    created_at: datetime


class FriendListResponse(BaseModel):
    items: list[FriendResponse]
    limit: int
    offset: int
    total: int


class BlockCreateRequest(BaseModel):
    blocked_id: uuid.UUID


class BlockResponse(BaseModel):
    id: uuid.UUID
    blocked_user: SocialUserSummary
    created_at: datetime


class BlockListResponse(BaseModel):
    items: list[BlockResponse]
    limit: int
    offset: int
    total: int


class UnblockResponse(BaseModel):
    unblocked: bool


class RemoveFriendResponse(BaseModel):
    removed: bool


class DirectConversationCreateRequest(BaseModel):
    user_id: uuid.UUID


class ConversationMemberResponse(BaseModel):
    user: SocialUserSummary
    role: str
    joined_at: datetime
    left_at: datetime | None


class MessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message body cannot be empty")
        return normalized


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: SocialUserSummary
    body: str | None
    message_type: str
    created_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    type: str
    members: list[ConversationMemberResponse]
    last_message: MessageResponse | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    limit: int
    offset: int
    total: int


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    limit: int
    offset: int
    total: int


class MarkReadResponse(BaseModel):
    conversation_id: uuid.UUID
    read_count: int
    read_at: datetime


class DeleteMessageResponse(BaseModel):
    id: uuid.UUID
    deleted: bool
    deleted_at: datetime | None
