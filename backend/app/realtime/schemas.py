import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RealtimeEventResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str
    type: str
    payload: dict[str, Any]
    delivered_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RealtimeEventListResponse(BaseModel):
    items: list[RealtimeEventResponse]
    limit: int
    offset: int
    total: int
