import uuid

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.common.rate_limit import enforce_user_rate_limit
from app.config import get_settings
from app.database import get_db_session
from app.pgn.schemas import (
    GameDetailResponse,
    GameListResponse,
    GameMoveResponse,
    PgnImportListResponse,
    PgnPasteRequest,
)
from app.pgn.services import (
    get_game_detail,
    get_game_moves,
    list_admin_games,
    list_admin_pgn_imports,
    list_user_games,
    list_user_pgn_imports,
    paste_pgn,
    upload_pgn,
)
from app.users.models import User

router = APIRouter(tags=["Games/PGN"])


@router.post(
    "/games/pgn/paste",
    response_model=GameDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def paste_pgn_game(
    payload: PgnPasteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GameDetailResponse:
    settings = get_settings()
    await enforce_user_rate_limit(
        request,
        user=current_user,
        scope="pgn",
        limit=settings.rate_limit_pgn_per_hour,
        window_seconds=3600,
    )
    return await paste_pgn(session=session, user_id=current_user.id, pgn_text=payload.pgn_text)


@router.post(
    "/games/pgn/upload",
    response_model=GameDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pgn_game(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GameDetailResponse:
    settings = get_settings()
    await enforce_user_rate_limit(
        request,
        user=current_user,
        scope="pgn",
        limit=settings.rate_limit_pgn_per_hour,
        window_seconds=3600,
    )
    return await upload_pgn(session=session, user_id=current_user.id, upload=file)


@router.get("/games", response_model=GameListResponse)
async def my_games(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GameListResponse:
    return await list_user_games(
        session=session,
        user=current_user,
        source=source,
        limit=limit,
        offset=offset,
    )


@router.get("/games/{game_id}", response_model=GameDetailResponse)
async def game_detail(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GameDetailResponse:
    return await get_game_detail(session=session, user=current_user, game_id=game_id)


@router.get("/games/{game_id}/moves", response_model=list[GameMoveResponse])
async def game_moves(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[GameMoveResponse]:
    return await get_game_moves(session=session, user=current_user, game_id=game_id)


@router.get("/pgn-imports", response_model=PgnImportListResponse)
async def my_pgn_imports(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PgnImportListResponse:
    return await list_user_pgn_imports(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/games", response_model=GameListResponse)
async def admin_games(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    source: str | None = None,
    user_id: uuid.UUID | None = None,
    tournament_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GameListResponse:
    _ = current_admin
    return await list_admin_games(
        session=session,
        source=source,
        user_id=user_id,
        tournament_id=tournament_id,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/pgn-imports", response_model=PgnImportListResponse)
async def admin_pgn_imports(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PgnImportListResponse:
    _ = current_admin
    return await list_admin_pgn_imports(
        session=session,
        user_id=user_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
