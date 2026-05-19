import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

FileType = Literal["avatar", "news_image", "tournament_image", "pgn", "export", "other"]


class FileMetadataResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None
    file_type: str
    storage_provider: str
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
