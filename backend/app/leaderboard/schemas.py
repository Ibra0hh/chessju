import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SeasonCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    starts_at: datetime
    ends_at: datetime | None = None
    active: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Season name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_dates(self) -> "SeasonCreateRequest":
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SeasonUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Season name cannot be blank")
        return normalized


class SeasonResponse(BaseModel):
    id: uuid.UUID
    name: str
    starts_at: datetime
    ends_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeasonListResponse(BaseModel):
    items: list[SeasonResponse]
    limit: int
    offset: int
    total: int


class LeaderboardRecomputeRequest(BaseModel):
    season_id: uuid.UUID | None = None


class LeaderboardRowResponse(BaseModel):
    rank: int
    user_id: uuid.UUID
    username: str
    full_name: str
    points: float
    rating: int
    wins: int
    draws: int
    losses: int
    byes: int
    games_played: int
    tournaments_played: int


class LeaderboardResponse(BaseModel):
    season: SeasonResponse | None
    generated_at: datetime | None
    rows: list[LeaderboardRowResponse]
    limit: int
    offset: int
    total: int
