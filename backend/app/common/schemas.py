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
