import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ChessComSyncJobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class ChessComConnectRequest(BaseModel):
    username: str = Field(min_length=2, max_length=200)


class ChessComSyncRequest(BaseModel):
    months: int | None = Field(default=None, ge=1)


class ChessComAccountResponse(BaseModel):
    id: uuid.UUID
    username: str
    profile_url: str | None
    title: str | None = None
    country: str | None = None
    avatar_url: str | None
    verified: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChessComSyncJobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chesscom_account_id: uuid.UUID
    status: ChessComSyncJobStatus
    archive_months_requested: int | None
    games_found: int
    games_imported: int
    games_skipped: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ChessComSyncJobListResponse(BaseModel):
    items: list[ChessComSyncJobResponse]
    limit: int
    offset: int
    total: int


class ChessComImportedGameResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    chesscom_url: str
    played_at: datetime | None
    time_class: str | None
    time_control: str | None
    rated: bool | None
    white_username: str | None
    black_username: str | None
    result: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChessComImportedGameListResponse(BaseModel):
    items: list[ChessComImportedGameResponse]
    limit: int
    offset: int
    total: int


class AdminChessComAccountResponse(ChessComAccountResponse):
    user_id: uuid.UUID
    disconnected_at: datetime | None


class AdminChessComAccountListResponse(BaseModel):
    items: list[AdminChessComAccountResponse]
    limit: int
    offset: int
    total: int


class AdminChessComImportedGameResponse(ChessComImportedGameResponse):
    user_id: uuid.UUID
    chesscom_account_id: uuid.UUID
    chesscom_uuid: str | None


class AdminChessComImportedGameListResponse(BaseModel):
    items: list[AdminChessComImportedGameResponse]
    limit: int
    offset: int
    total: int


class ChessComUsernameMixin(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("username cannot be blank")
        return value
