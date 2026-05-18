from fastapi import FastAPI, HTTPException, status

from app.common.schemas import DatabaseHealthResponse, HealthResponse, VersionResponse
from app.config import get_settings
from app.database import check_database_connection

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


@app.get("/health", response_model=HealthResponse, tags=["operations"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@app.get("/version", response_model=VersionResponse, tags=["operations"])
async def version() -> VersionResponse:
    return VersionResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@app.get("/health/db", response_model=DatabaseHealthResponse, tags=["operations"])
async def database_health() -> DatabaseHealthResponse:
    is_connected = await check_database_connection()
    if not is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unavailable", "database": "postgresql"},
        )

    return DatabaseHealthResponse(status="ok", database="postgresql")
