from fastapi import FastAPI, HTTPException, status

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.common.schemas import DatabaseHealthResponse, HealthResponse, VersionResponse
from app.config import get_settings
from app.database import check_database_connection
from app.files.router import router as files_router
from app.news.router import router as news_router
from app.users.router import router as users_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth")
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(files_router, prefix=settings.api_v1_prefix)
app.include_router(news_router, prefix=settings.api_v1_prefix)


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
