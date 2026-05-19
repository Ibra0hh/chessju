import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import chess
import chess.pgn
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import ADMIN_ROLE_NAMES
from app.files.models import FileRecord
from app.files.services import (
    create_file_record_from_validated_upload,
    read_validated_upload,
    remove_stored_file,
)
from app.games.models import Game, GameMove
from app.pgn.models import PgnImport
from app.pgn.schemas import (
    GameDetailResponse,
    GameListResponse,
    GameMoveResponse,
    GameSummaryResponse,
    PgnImportListResponse,
    PgnImportResponse,
)
from app.users.models import User
from app.users.services import get_role_names_for_user

MAX_PGN_PASTE_BYTES = 200 * 1024
MAX_PGN_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_GAME_SOURCES = {"tournament", "pgn_upload", "chesscom_import", "manual"}
PGN_METADATA_HEADERS = {
    "Event",
    "Site",
    "Date",
    "Round",
    "White",
    "Black",
    "Result",
    "ECO",
    "Opening",
    "TimeControl",
}


@dataclass(frozen=True)
class ParsedMove:
    ply_number: int
    move_number: int
    side: str
    san: str
    uci: str
    fen_before: str
    fen_after: str
    is_check: bool
    is_checkmate: bool
    comment: str | None


@dataclass(frozen=True)
class ParsedPgnGame:
    metadata: dict[str, str]
    initial_fen: str
    final_fen: str
    moves: list[ParsedMove]
    played_at: datetime | None


def _validate_source_filter(source: str | None) -> None:
    if source is not None and source not in ALLOWED_GAME_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid game source",
        )


def _pgn_size_bytes(pgn_text: str) -> int:
    return len(pgn_text.encode("utf-8"))


def _parse_pgn_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) != 3 or any(part == "??" for part in parts):
        return None
    try:
        year, month, day = (int(part) for part in parts)
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


def parse_pgn_text(pgn_text: str) -> ParsedPgnGame:
    if not pgn_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PGN cannot be empty")
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PGN") from exc
    if game is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PGN")
    if getattr(game, "errors", None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PGN")

    metadata = {
        header: str(game.headers[header])
        for header in PGN_METADATA_HEADERS
        if header in game.headers and str(game.headers[header]).strip()
    }
    board = game.board()
    initial_fen = board.fen()
    moves: list[ParsedMove] = []
    for ply_number, node in enumerate(game.mainline(), start=1):
        move = node.move
        fen_before = board.fen()
        side = "white" if board.turn == chess.WHITE else "black"
        move_number = board.fullmove_number
        try:
            san = board.san(move)
        except AssertionError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PGN",
            ) from exc
        board.push(move)
        moves.append(
            ParsedMove(
                ply_number=ply_number,
                move_number=move_number,
                side=side,
                san=san,
                uci=move.uci(),
                fen_before=fen_before,
                fen_after=board.fen(),
                is_check=board.is_check(),
                is_checkmate=board.is_checkmate(),
                comment=node.comment.strip() or None,
            )
        )
    if not moves:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PGN must contain at least one legal move",
        )
    return ParsedPgnGame(
        metadata=metadata,
        initial_fen=initial_fen,
        final_fen=board.fen(),
        moves=moves,
        played_at=_parse_pgn_date(metadata.get("Date")),
    )


def _metadata_field(game: Game, key: str) -> str | None:
    value = game.game_metadata.get(key)
    return str(value) if value else None


async def _moves_count(session: AsyncSession, game_id: uuid.UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(GameMove).where(GameMove.game_id == game_id)
    )
    return count or 0


async def build_game_summary(session: AsyncSession, game: Game) -> GameSummaryResponse:
    return GameSummaryResponse(
        id=game.id,
        source=game.source,
        white_name=game.white_name,
        black_name=game.black_name,
        result=game.result,
        event=_metadata_field(game, "Event"),
        site=_metadata_field(game, "Site"),
        date=_metadata_field(game, "Date"),
        round=_metadata_field(game, "Round"),
        eco_code=game.eco_code,
        opening_name=game.opening_name,
        time_control=_metadata_field(game, "TimeControl"),
        played_at=game.played_at,
        created_at=game.created_at,
        moves_count=await _moves_count(session, game.id),
    )


async def build_game_detail(session: AsyncSession, game: Game) -> GameDetailResponse:
    summary = await build_game_summary(session, game)
    result = await session.execute(
        select(GameMove).where(GameMove.game_id == game.id).order_by(GameMove.ply_number.asc())
    )
    return GameDetailResponse(
        **summary.model_dump(),
        metadata={str(key): str(value) for key, value in game.game_metadata.items()},
        initial_fen=game.initial_fen,
        final_fen=game.final_fen,
        moves=[GameMoveResponse.model_validate(move) for move in result.scalars()],
    )


async def _create_game_from_parsed_pgn(
    session: AsyncSession,
    user_id: uuid.UUID,
    pgn_text: str,
    parsed: ParsedPgnGame,
    import_source: str,
    file_record: FileRecord | None = None,
) -> GameDetailResponse:
    game = Game(
        owner_id=user_id,
        white_name=parsed.metadata.get("White"),
        black_name=parsed.metadata.get("Black"),
        result=parsed.metadata.get("Result"),
        source="pgn_upload",
        pgn_text=pgn_text,
        pgn_file_id=file_record.id if file_record else None,
        played_at=parsed.played_at,
        eco_code=parsed.metadata.get("ECO"),
        opening_name=parsed.metadata.get("Opening"),
        game_metadata=parsed.metadata,
        initial_fen=parsed.initial_fen,
        final_fen=parsed.final_fen,
    )
    session.add(game)
    await session.flush()
    session.add_all(
        [
            GameMove(
                game_id=game.id,
                ply_number=move.ply_number,
                move_number=move.move_number,
                side=move.side,
                san=move.san,
                uci=move.uci,
                fen_before=move.fen_before,
                fen_after=move.fen_after,
                is_check=move.is_check,
                is_checkmate=move.is_checkmate,
                comment=move.comment,
            )
            for move in parsed.moves
        ]
    )
    pgn_import = PgnImport(
        user_id=user_id,
        source=import_source,
        status="parsed",
        file_id=file_record.id if file_record else None,
        game_id=game.id,
        completed_at=datetime.now(UTC),
    )
    session.add(pgn_import)
    await session.commit()
    await session.refresh(game)
    return await build_game_detail(session, game)


async def paste_pgn(
    session: AsyncSession,
    user_id: uuid.UUID,
    pgn_text: str,
) -> GameDetailResponse:
    if _pgn_size_bytes(pgn_text) > MAX_PGN_PASTE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="PGN paste is too large",
        )
    parsed = parse_pgn_text(pgn_text)
    return await _create_game_from_parsed_pgn(
        session=session,
        user_id=user_id,
        pgn_text=pgn_text,
        parsed=parsed,
        import_source="paste",
    )


async def upload_pgn(
    session: AsyncSession,
    user_id: uuid.UUID,
    upload: UploadFile,
) -> GameDetailResponse:
    validated_upload = await read_validated_upload("pgn", upload, max_bytes=MAX_PGN_FILE_BYTES)
    try:
        pgn_text = validated_upload.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PGN file must be UTF-8 text",
        ) from exc
    parsed = parse_pgn_text(pgn_text)
    file_record: FileRecord | None = None
    try:
        file_record = await create_file_record_from_validated_upload(
            session=session,
            owner_id=user_id,
            file_type="pgn",
            upload=validated_upload,
        )
        return await _create_game_from_parsed_pgn(
            session=session,
            user_id=user_id,
            pgn_text=pgn_text,
            parsed=parsed,
            import_source="file_upload",
            file_record=file_record,
        )
    except Exception:
        await session.rollback()
        if file_record is not None:
            await remove_stored_file(file_record)
        raise


async def _is_admin_user(session: AsyncSession, user: User) -> bool:
    return bool(set(await get_role_names_for_user(session, user.id)).intersection(ADMIN_ROLE_NAMES))


async def can_view_game(session: AsyncSession, user: User, game: Game) -> bool:
    if await _is_admin_user(session, user):
        return True
    if game.owner_id == user.id:
        return True
    return game.white_user_id == user.id or game.black_user_id == user.id


async def get_authorized_game(session: AsyncSession, user: User, game_id: uuid.UUID) -> Game:
    game = await session.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if not await can_view_game(session, user, game):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


def _user_games_statement(user: User, source: str | None = None) -> Select[tuple[Game]]:
    statement = select(Game).where(
        or_(Game.owner_id == user.id, Game.white_user_id == user.id, Game.black_user_id == user.id)
    )
    if source is not None:
        statement = statement.where(Game.source == source)
    return statement


async def list_user_games(
    session: AsyncSession,
    user: User,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> GameListResponse:
    _validate_source_filter(source)
    statement = _user_games_statement(user, source)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Game.created_at.desc(), Game.id.desc()).limit(limit).offset(offset)
    )
    return GameListResponse(
        items=[await build_game_summary(session, game) for game in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_admin_games(
    session: AsyncSession,
    source: str | None = None,
    user_id: uuid.UUID | None = None,
    tournament_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> GameListResponse:
    _validate_source_filter(source)
    statement = select(Game)
    if source is not None:
        statement = statement.where(Game.source == source)
    if user_id is not None:
        statement = statement.where(
            or_(
                Game.owner_id == user_id,
                Game.white_user_id == user_id,
                Game.black_user_id == user_id,
            )
        )
    if tournament_id is not None:
        statement = statement.where(Game.tournament_id == tournament_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Game.created_at.desc(), Game.id.desc()).limit(limit).offset(offset)
    )
    return GameListResponse(
        items=[await build_game_summary(session, game) for game in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_game_detail(
    session: AsyncSession,
    user: User,
    game_id: uuid.UUID,
) -> GameDetailResponse:
    game = await get_authorized_game(session, user, game_id)
    return await build_game_detail(session, game)


async def get_game_moves(
    session: AsyncSession,
    user: User,
    game_id: uuid.UUID,
) -> list[GameMoveResponse]:
    game = await get_authorized_game(session, user, game_id)
    result = await session.execute(
        select(GameMove).where(GameMove.game_id == game.id).order_by(GameMove.ply_number.asc())
    )
    return [GameMoveResponse.model_validate(move) for move in result.scalars()]


async def list_user_pgn_imports(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> PgnImportListResponse:
    statement = select(PgnImport).where(PgnImport.user_id == user_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(PgnImport.created_at.desc(), PgnImport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return PgnImportListResponse(
        items=[PgnImportResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_admin_pgn_imports(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PgnImportListResponse:
    statement = select(PgnImport)
    if user_id is not None:
        statement = statement.where(PgnImport.user_id == user_id)
    if status_filter is not None:
        statement = statement.where(PgnImport.status == status_filter)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(PgnImport.created_at.desc(), PgnImport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return PgnImportListResponse(
        items=[PgnImportResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )
