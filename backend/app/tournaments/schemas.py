import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TournamentStatus = Literal[
    "draft",
    "published",
    "registration_open",
    "registration_closed",
    "check_in",
    "in_progress",
    "completed",
    "cancelled",
]
TournamentCreateStatus = Literal["draft", "published", "registration_open", "registration_closed"]
TournamentFormat = Literal["swiss", "round_robin", "knockout", "arena", "manual"]
TimeControlType = Literal["bullet", "blitz", "rapid", "classical", "custom"]
RegistrationStatus = Literal["pending", "approved", "waitlisted", "cancelled", "rejected"]
RoundStatus = Literal["draft", "published", "in_progress", "completed", "cancelled"]
PairingStatus = Literal["scheduled", "active", "completed", "disputed", "cancelled"]
PairingResult = Literal[
    "pending",
    "white_win",
    "black_win",
    "draw",
    "white_forfeit",
    "black_forfeit",
    "double_forfeit",
    "bye",
]
PairingGenerationMethod = Literal["swiss", "round_robin"]

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TimeControlCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_seconds: int = Field(gt=0)
    increment_seconds: int = Field(default=0, ge=0)
    delay_seconds: int = Field(default=0, ge=0)
    type: TimeControlType

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be blank")
        return normalized


class TimeControlUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_seconds: int | None = Field(default=None, gt=0)
    increment_seconds: int | None = Field(default=None, ge=0)
    delay_seconds: int | None = Field(default=None, ge=0)
    type: TimeControlType | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be blank")
        return normalized


class TimeControlResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_seconds: int
    increment_seconds: int
    delay_seconds: int
    type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeControlListResponse(BaseModel):
    items: list[TimeControlResponse]
    limit: int
    offset: int
    total: int


class TournamentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = Field(default=None, max_length=5000)
    status: TournamentCreateStatus = "draft"
    format: TournamentFormat
    time_control_id: uuid.UUID | None = None
    max_players: int | None = Field(default=None, gt=0)
    starts_at: datetime
    ends_at: datetime | None = None
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    cover_file_id: uuid.UUID | None = None

    @field_validator("title", "slug", "description", "location")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("Slug must use lowercase letters, numbers, and hyphens")
        return normalized

    @model_validator(mode="after")
    def validate_dates(self) -> "TournamentCreateRequest":
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.registration_close_at is not None and self.registration_close_at >= self.starts_at:
            raise ValueError("registration_close_at must be before starts_at")
        return self


class TournamentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = Field(default=None, max_length=5000)
    format: TournamentFormat | None = None
    time_control_id: uuid.UUID | None = None
    max_players: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    registration_open_at: datetime | None = None
    registration_close_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    cover_file_id: uuid.UUID | None = None

    @field_validator("title", "slug", "description", "location")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text fields cannot be blank")
        return normalized

    @field_validator("slug")
    @classmethod
    def validate_optional_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("Slug must use lowercase letters, numbers, and hyphens")
        return normalized


class TournamentRegistrationUpdateRequest(BaseModel):
    status: RegistrationStatus
    seed_rating: int | None = Field(default=None, ge=0)
    checked_in_at: datetime | None = None


class TournamentRegistrationResponse(BaseModel):
    id: uuid.UUID
    tournament_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    seed_rating: int | None
    checked_in_at: datetime | None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TournamentSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    status: str
    format: str
    starts_at: datetime
    location: str | None
    cover_file_id: uuid.UUID | None
    time_control: TimeControlResponse | None
    max_players: int | None
    approved_count: int
    waitlisted_count: int
    spots_remaining: int | None


class TournamentDetailResponse(TournamentSummaryResponse):
    description: str | None
    ends_at: datetime | None
    registration_open_at: datetime | None
    registration_close_at: datetime | None
    created_at: datetime
    my_registration: TournamentRegistrationResponse | None = None


class AdminTournamentResponse(TournamentDetailResponse):
    created_by: uuid.UUID
    updated_at: datetime
    deleted_at: datetime | None


class TournamentListResponse(BaseModel):
    items: list[TournamentSummaryResponse]
    limit: int
    offset: int
    total: int


class AdminTournamentListResponse(BaseModel):
    items: list[AdminTournamentResponse]
    limit: int
    offset: int
    total: int


class TournamentRegistrationListResponse(BaseModel):
    items: list[TournamentRegistrationResponse]
    limit: int
    offset: int
    total: int


class UserTournamentRegistrationResponse(BaseModel):
    registration: TournamentRegistrationResponse
    tournament: TournamentSummaryResponse


class UserTournamentRegistrationListResponse(BaseModel):
    items: list[UserTournamentRegistrationResponse]
    limit: int
    offset: int
    total: int


class DeleteTournamentResponse(BaseModel):
    deleted: bool


class PlayerSummaryResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str


class RoundCreateRequest(BaseModel):
    round_number: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title cannot be blank")
        return normalized


class RoundUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None
    status: RoundStatus | None = None

    @field_validator("title")
    @classmethod
    def strip_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title cannot be blank")
        return normalized


class RoundResponse(BaseModel):
    id: uuid.UUID
    tournament_id: uuid.UUID
    round_number: int
    title: str | None
    status: str
    starts_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoundListResponse(BaseModel):
    items: list[RoundResponse]
    limit: int
    offset: int
    total: int


class PairingCreateRequest(BaseModel):
    board_number: int | None = Field(default=None, gt=0)
    white_user_id: uuid.UUID | None = None
    black_user_id: uuid.UUID | None = None
    result: PairingResult = "pending"


class PairingBulkCreateRequest(BaseModel):
    pairings: list[PairingCreateRequest] = Field(min_length=1, max_length=200)


class PairingGenerateRequest(BaseModel):
    method: PairingGenerationMethod = "swiss"
    overwrite_existing: bool = False


class PairingUpdateRequest(BaseModel):
    board_number: int | None = Field(default=None, gt=0)
    white_user_id: uuid.UUID | None = None
    black_user_id: uuid.UUID | None = None
    status: PairingStatus | None = None


class ResultSubmitRequest(BaseModel):
    result: PairingResult


class PairingResponse(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    tournament_id: uuid.UUID
    board_number: int
    white_user: PlayerSummaryResponse | None
    black_user: PlayerSummaryResponse | None
    status: str
    result: str
    result_reported_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PairingListResponse(BaseModel):
    items: list[PairingResponse]
    limit: int
    offset: int
    total: int


class RoundDetailResponse(RoundResponse):
    pairings: list[PairingResponse]


class StandingRowResponse(BaseModel):
    rank: int
    user_id: uuid.UUID
    username: str
    full_name: str
    points: float
    wins: int
    losses: int
    draws: int
    byes: int
    games_played: int


class StandingsResponse(BaseModel):
    tournament_id: uuid.UUID
    items: list[StandingRowResponse]


class UserPairingListResponse(BaseModel):
    items: list[PairingResponse]
    limit: int
    offset: int
    total: int
