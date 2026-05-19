import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ClockColor = Literal["white", "black", "none"]
ClockSessionStatus = Literal["setup", "running", "paused", "completed", "cancelled"]
ClockSessionResult = Literal[
    "white_flagged",
    "black_flagged",
    "white_win",
    "black_win",
    "draw",
    "aborted",
    "manual",
]
ClockEventType = Literal[
    "setup",
    "start",
    "pause",
    "resume",
    "switch_turn",
    "adjust_time",
    "flag",
    "reset",
    "complete",
    "cancel",
]


class ClockSessionCreateRequest(BaseModel):
    tournament_id: uuid.UUID | None = None
    pairing_id: uuid.UUID | None = None
    white_user_id: uuid.UUID | None = None
    black_user_id: uuid.UUID | None = None
    base_seconds: int = Field(gt=0)
    increment_seconds: int = Field(default=0, ge=0)
    delay_seconds: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def reject_same_player_ids(self) -> "ClockSessionCreateRequest":
        if self.white_user_id is not None and self.white_user_id == self.black_user_id:
            raise ValueError("white_user_id and black_user_id must be different")
        return self


class ClockSnapshotRequest(BaseModel):
    white_remaining_ms: int = Field(ge=0)
    black_remaining_ms: int = Field(ge=0)
    client_timestamp: datetime | None = None


class ClockStartRequest(ClockSnapshotRequest):
    active_color: Literal["white", "black"] = "white"


class ClockResumeRequest(ClockSnapshotRequest):
    active_color: Literal["white", "black"] | None = None


class ClockSwitchTurnRequest(ClockSnapshotRequest):
    active_color: Literal["white", "black"]


class ClockAdjustRequest(ClockSnapshotRequest):
    reason: str | None = Field(default=None, max_length=500)


class ClockFlagRequest(ClockSnapshotRequest):
    flagged_color: Literal["white", "black"]


class ClockCompleteRequest(ClockSnapshotRequest):
    result: ClockSessionResult

    @model_validator(mode="after")
    def reject_flag_results(self) -> "ClockCompleteRequest":
        if self.result in {"white_flagged", "black_flagged"}:
            raise ValueError("Use the flag endpoint for flag results")
        return self


class ClockResetRequest(BaseModel):
    client_timestamp: datetime | None = None


class ClockCancelRequest(ClockSnapshotRequest):
    reason: str | None = Field(default=None, max_length=500)


class ClockSessionResponse(BaseModel):
    id: uuid.UUID
    tournament_id: uuid.UUID | None
    pairing_id: uuid.UUID | None
    white_user_id: uuid.UUID | None
    black_user_id: uuid.UUID | None
    base_seconds: int
    increment_seconds: int
    delay_seconds: int
    white_remaining_ms: int
    black_remaining_ms: int
    active_color: str
    status: str
    result: str | None
    created_by: uuid.UUID
    last_event_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClockSessionListResponse(BaseModel):
    items: list[ClockSessionResponse]
    limit: int
    offset: int
    total: int


class ClockEventResponse(BaseModel):
    id: uuid.UUID
    clock_session_id: uuid.UUID
    event_type: str
    actor_user_id: uuid.UUID | None
    white_remaining_ms: int
    black_remaining_ms: int
    active_color: str
    client_timestamp: datetime | None
    server_timestamp: datetime
    metadata: dict[str, Any]


class ClockEventListResponse(BaseModel):
    items: list[ClockEventResponse]
    limit: int
    offset: int
    total: int
