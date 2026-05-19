import logging
import time

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin.router import router as admin_router
from app.analysis.router import router as analysis_router
from app.auth.router import router as auth_router
from app.chesscom.router import router as chesscom_router
from app.clock.router import router as clock_router
from app.common.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.common.request_context import (
    REQUEST_ID_HEADER,
    normalize_request_id,
    request_id_context,
)
from app.common.schemas import (
    DatabaseHealthResponse,
    HealthResponse,
    ValkeyHealthResponse,
    VersionResponse,
)
from app.config import get_settings
from app.database import check_database_connection
from app.files.router import router as files_router
from app.leaderboard.router import router as leaderboard_router
from app.news.router import router as news_router
from app.notifications.router import router as notifications_router
from app.pgn.router import router as pgn_router
from app.realtime.router import router as realtime_router
from app.social.router import router as social_router
from app.tournaments.router import router as tournaments_router
from app.users.router import router as users_router
from app.valkey import check_valkey_connection

settings = get_settings()
logger = logging.getLogger("chessju.api")

OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness, version, and dependency health checks."},
    {"name": "Auth", "description": "Custom JWT authentication and refresh tokens."},
    {"name": "Users", "description": "Current user profile and preferences."},
    {"name": "Admin", "description": "Admin identity and audit logs."},
    {"name": "Files", "description": "Local file metadata and admin uploads."},
    {"name": "News", "description": "News, announcements, and home content."},
    {"name": "Tournaments", "description": "Tournaments, registrations, rounds, and pairings."},
    {"name": "Leaderboard", "description": "JU leaderboard seasons and snapshots."},
    {"name": "Games/PGN", "description": "PGN import and game library endpoints."},
    {"name": "Analysis", "description": "Stockfish analysis jobs and reports."},
    {"name": "Chess.com", "description": "Public Chess.com account and game import."},
    {"name": "Clock", "description": "Chess clock sessions and event logs."},
    {"name": "Social/Chat", "description": "Friends, blocks, conversations, and messages."},
    {"name": "Notifications", "description": "In-app notifications and preferences."},
    {"name": "Realtime", "description": "SSE streams and realtime event outbox."},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_method_list(),
    allow_headers=settings.cors_header_list(),
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth")
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(files_router, prefix=settings.api_v1_prefix)
app.include_router(news_router, prefix=settings.api_v1_prefix)
app.include_router(tournaments_router, prefix=settings.api_v1_prefix)
app.include_router(leaderboard_router, prefix=settings.api_v1_prefix)
app.include_router(pgn_router, prefix=settings.api_v1_prefix)
app.include_router(analysis_router, prefix=settings.api_v1_prefix)
app.include_router(chesscom_router, prefix=settings.api_v1_prefix)
app.include_router(clock_router, prefix=settings.api_v1_prefix)
app.include_router(social_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)
app.include_router(realtime_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_context.reset(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
    return response


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@app.get("/version", response_model=VersionResponse, tags=["Health"])
async def version() -> VersionResponse:
    return VersionResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@app.get("/health/db", response_model=DatabaseHealthResponse, tags=["Health"])
async def database_health() -> DatabaseHealthResponse:
    is_connected = await check_database_connection()
    if not is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unavailable", "database": "postgresql"},
        )

    return DatabaseHealthResponse(status="ok", database="postgresql")


@app.get("/health/valkey", response_model=ValkeyHealthResponse, tags=["Health"])
async def valkey_health() -> ValkeyHealthResponse:
    is_connected = await check_valkey_connection()
    if not is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unavailable", "valkey": "valkey"},
        )

    return ValkeyHealthResponse(status="ok", valkey="valkey")
