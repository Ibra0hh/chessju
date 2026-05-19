import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GameSource = Literal["tournament", "pgn_upload", "chesscom_import", "manual"]
PgnImportSource = Literal["paste", "file_upload"]
PgnImportStatus = Literal["pending", "parsed", "failed"]


class PgnPasteRequest(BaseModel):
    pgn_text: str = Field(min_length=1)


class GameMoveResponse(BaseModel):
    id: uuid.UUID | None = None
    ply_number: int
    move_number: int
    side: str
    san: str
    uci: str
    fen_before: str
    fen_after: str
    is_check: bool
    is_checkmate: bool
    comment: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GameSummaryResponse(BaseModel):
    id: uuid.UUID
    source: str
    white_name: str | None
    black_name: str | None
    result: str | None
    event: str | None
    site: str | None
    date: str | None
    round: str | None
    eco_code: str | None
    opening_name: str | None
    time_control: str | None
    played_at: datetime | None
    created_at: datetime
    moves_count: int


class GameListResponse(BaseModel):
    items: list[GameSummaryResponse]
    limit: int
    offset: int
    total: int


class GameDetailResponse(GameSummaryResponse):
    metadata: dict[str, str]
    initial_fen: str | None
    final_fen: str | None
    moves: list[GameMoveResponse]


class PgnImportResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    source: str
    status: str
    file_id: uuid.UUID | None
    game_id: uuid.UUID | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PgnImportListResponse(BaseModel):
    items: list[PgnImportResponse]
    limit: int
    offset: int
    total: int
