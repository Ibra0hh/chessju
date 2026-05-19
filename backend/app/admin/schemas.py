import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminIdentityResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    roles: list[str]
    username: str
    full_name: str


class AdminActionLogResponse(BaseModel):
    id: uuid.UUID
    admin_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminActionLogListResponse(BaseModel):
    items: list[AdminActionLogResponse]
    limit: int
    offset: int
    total: int


class AuditLogFilters(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    action: str | None = Field(default=None, min_length=1, max_length=100)
    entity_type: str | None = Field(default=None, min_length=1, max_length=100)
    admin_id: uuid.UUID | None = None
