from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    app_name: str
    version: str
    environment: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class ValkeyHealthResponse(BaseModel):
    status: str
    valkey: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any]
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class PaginationMetadata(BaseModel):
    limit: int
    offset: int
    count: int
