import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import create_admin_action_log
from app.common.time import utc_now
from app.games.models import Game
from app.leaderboard.models import LeaderboardSnapshot, PlayerRating, Season
from app.leaderboard.schemas import (
    LeaderboardResponse,
    LeaderboardRowResponse,
    SeasonCreateRequest,
    SeasonListResponse,
    SeasonResponse,
    SeasonUpdateRequest,
)
from app.tournaments.models import Pairing, Tournament, TournamentRegistration
from app.users.models import Profile

SCORING_RESULTS = {
    "white_win",
    "black_win",
    "draw",
    "white_forfeit",
    "black_forfeit",
    "double_forfeit",
    "bye",
}


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def season_audit_snapshot(season: Season) -> dict[str, Any]:
    return {
        "id": str(season.id),
        "name": season.name,
        "starts_at": _dt(season.starts_at),
        "ends_at": _dt(season.ends_at),
        "active": season.active,
        "created_at": _dt(season.created_at),
        "updated_at": _dt(season.updated_at),
    }


def _validate_season_dates(starts_at: datetime, ends_at: datetime | None) -> None:
    if ends_at is not None and ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ends_at must be after starts_at",
        )


async def get_season(session: AsyncSession, season_id: uuid.UUID) -> Season:
    season = await session.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


async def get_active_season(session: AsyncSession) -> Season | None:
    result = await session.execute(select(Season).where(Season.active.is_(True)))
    return result.scalar_one_or_none()


async def create_season(
    session: AsyncSession,
    admin_id: uuid.UUID,
    payload: SeasonCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SeasonResponse:
    if payload.active:
        await session.execute(update(Season).values(active=False))
    season = Season(
        name=payload.name,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        active=payload.active,
    )
    session.add(season)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="season.created",
        entity_type="season",
        entity_id=season.id,
        after=season_audit_snapshot(season),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(season)
    return SeasonResponse.model_validate(season)


async def list_seasons(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> SeasonListResponse:
    total = await session.scalar(select(func.count()).select_from(Season))
    result = await session.execute(
        select(Season)
        .order_by(Season.starts_at.desc(), Season.created_at.desc(), Season.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return SeasonListResponse(
        items=[SeasonResponse.model_validate(season) for season in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def update_season(
    session: AsyncSession,
    admin_id: uuid.UUID,
    season_id: uuid.UUID,
    payload: SeasonUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SeasonResponse:
    season = await get_season(session, season_id)
    next_starts_at = payload.starts_at if payload.starts_at is not None else season.starts_at
    next_ends_at = payload.ends_at if "ends_at" in payload.model_fields_set else season.ends_at
    _validate_season_dates(next_starts_at, next_ends_at)
    before = season_audit_snapshot(season)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(season, field_name, value)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="season.updated",
        entity_type="season",
        entity_id=season.id,
        before=before,
        after=season_audit_snapshot(season),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(season)
    return SeasonResponse.model_validate(season)


async def activate_season(
    session: AsyncSession,
    admin_id: uuid.UUID,
    season_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SeasonResponse:
    season = await get_season(session, season_id)
    before = season_audit_snapshot(season)
    await session.execute(update(Season).values(active=False))
    season.active = True
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="season.activated",
        entity_type="season",
        entity_id=season.id,
        before=before,
        after=season_audit_snapshot(season),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(season)
    return SeasonResponse.model_validate(season)


def _base_tournament_filters(season: Season | None) -> list[Any]:
    filters: list[Any] = [
        Tournament.deleted_at.is_(None),
        Tournament.status != "cancelled",
    ]
    if season is not None:
        filters.append(Tournament.starts_at >= season.starts_at)
        if season.ends_at is not None:
            filters.append(Tournament.starts_at <= season.ends_at)
    return filters


def _empty_row(user_id: uuid.UUID, profile: Profile) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "username": profile.username,
        "full_name": profile.full_name,
        "points": 0.0,
        "rating": 1200,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "byes": 0,
        "games_played": 0,
        "tournaments_played": 0,
    }


def _add_win(row: dict[str, Any], points: float = 1.0) -> None:
    row["points"] += points
    row["wins"] += 1
    row["games_played"] += 1


def _add_loss(row: dict[str, Any]) -> None:
    row["losses"] += 1
    row["games_played"] += 1


def _add_draw(row: dict[str, Any]) -> None:
    row["points"] += 0.5
    row["draws"] += 1
    row["games_played"] += 1


async def _collect_approved_players(
    session: AsyncSession, season: Season | None
) -> tuple[dict[uuid.UUID, dict[str, Any]], dict[uuid.UUID, set[uuid.UUID]]]:
    result = await session.execute(
        select(TournamentRegistration.user_id, TournamentRegistration.tournament_id, Profile)
        .join(Tournament, Tournament.id == TournamentRegistration.tournament_id)
        .join(Profile, Profile.user_id == TournamentRegistration.user_id)
        .where(
            TournamentRegistration.status == "approved",
            and_(*_base_tournament_filters(season)),
        )
    )
    rows: dict[uuid.UUID, dict[str, Any]] = {}
    tournaments_by_user: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for user_id, tournament_id, profile in result.all():
        if user_id not in rows:
            rows[user_id] = _empty_row(user_id, profile)
        tournaments_by_user[user_id].add(tournament_id)
    for user_id, tournament_ids in tournaments_by_user.items():
        rows[user_id]["tournaments_played"] = len(tournament_ids)
    return rows, tournaments_by_user


async def _apply_internal_ratings(
    session: AsyncSession,
    rows: dict[uuid.UUID, dict[str, Any]],
) -> None:
    if not rows:
        return
    result = await session.execute(
        select(PlayerRating.user_id, PlayerRating.rating).where(
            PlayerRating.user_id.in_(rows.keys()),
            PlayerRating.rating_type == "internal",
        )
    )
    for user_id, rating in result.all():
        rows[user_id]["rating"] = rating


async def _apply_completed_pairings(
    session: AsyncSession,
    season: Season | None,
    rows: dict[uuid.UUID, dict[str, Any]],
) -> None:
    result = await session.execute(
        select(Pairing)
        .join(Game, Game.pairing_id == Pairing.id)
        .join(Tournament, Tournament.id == Pairing.tournament_id)
        .where(
            Pairing.status == "completed",
            Pairing.result.in_(SCORING_RESULTS),
            Game.source == "tournament",
            and_(*_base_tournament_filters(season)),
        )
    )
    seen_pairings: set[uuid.UUID] = set()
    for pairing in result.scalars():
        if pairing.id in seen_pairings:
            continue
        seen_pairings.add(pairing.id)
        white = rows.get(pairing.white_user_id) if pairing.white_user_id else None
        black = rows.get(pairing.black_user_id) if pairing.black_user_id else None
        match pairing.result:
            case "white_win":
                if white:
                    _add_win(white)
                if black:
                    _add_loss(black)
            case "black_win":
                if black:
                    _add_win(black)
                if white:
                    _add_loss(white)
            case "draw":
                if white:
                    _add_draw(white)
                if black:
                    _add_draw(black)
            case "white_forfeit":
                if black:
                    _add_win(black)
                if white:
                    _add_loss(white)
            case "black_forfeit":
                if white:
                    _add_win(white)
                if black:
                    _add_loss(black)
            case "double_forfeit":
                if white:
                    _add_loss(white)
                if black:
                    _add_loss(black)
            case "bye":
                player = white or black
                if player:
                    player["points"] += 1.0
                    player["wins"] += 1
                    player["byes"] += 1
                    player["games_played"] += 1


async def _compute_rows(
    session: AsyncSession,
    season: Season | None,
) -> list[dict[str, Any]]:
    rows, _ = await _collect_approved_players(session, season)
    await _apply_internal_ratings(session, rows)
    await _apply_completed_pairings(session, season, rows)
    return sorted(
        rows.values(),
        key=lambda row: (
            -row["points"],
            -row["wins"],
            -row["draws"],
            -row["games_played"],
            row["username"],
        ),
    )


async def recompute_leaderboard(
    session: AsyncSession,
    admin_id: uuid.UUID,
    season_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LeaderboardResponse:
    season = await get_season(session, season_id) if season_id is not None else None
    computed_rows = await _compute_rows(session, season)
    if season is None:
        await session.execute(
            delete(LeaderboardSnapshot).where(LeaderboardSnapshot.season_id.is_(None))
        )
    else:
        await session.execute(
            delete(LeaderboardSnapshot).where(LeaderboardSnapshot.season_id == season.id)
        )

    generated_at = utc_now()
    for index, row in enumerate(computed_rows, start=1):
        session.add(
            LeaderboardSnapshot(
                season_id=season.id if season else None,
                user_id=row["user_id"],
                rank=index,
                points=Decimal(str(row["points"])),
                rating=row["rating"],
                wins=row["wins"],
                draws=row["draws"],
                losses=row["losses"],
                byes=row["byes"],
                games_played=row["games_played"],
                tournaments_played=row["tournaments_played"],
                tie_breaks={},
                generated_at=generated_at,
            )
        )
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="leaderboard.recomputed",
        entity_type="leaderboard",
        entity_id=season.id if season else None,
        after={
            "season_id": str(season.id) if season else None,
            "rows": len(computed_rows),
            "generated_at": _dt(generated_at),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return await get_snapshot_leaderboard(session, season=season, limit=100, offset=0)


async def get_snapshot_leaderboard(
    session: AsyncSession,
    season: Season | None,
    limit: int = 50,
    offset: int = 0,
) -> LeaderboardResponse:
    season_filter = (
        LeaderboardSnapshot.season_id == season.id
        if season is not None
        else LeaderboardSnapshot.season_id.is_(None)
    )
    total = await session.scalar(
        select(func.count()).select_from(LeaderboardSnapshot).where(season_filter)
    )
    generated_at = await session.scalar(
        select(func.max(LeaderboardSnapshot.generated_at)).where(season_filter)
    )
    result = await session.execute(
        select(LeaderboardSnapshot, Profile)
        .join(Profile, Profile.user_id == LeaderboardSnapshot.user_id)
        .where(season_filter)
        .order_by(LeaderboardSnapshot.rank.asc(), LeaderboardSnapshot.id.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = [
        LeaderboardRowResponse(
            rank=snapshot.rank,
            user_id=snapshot.user_id,
            username=profile.username,
            full_name=profile.full_name,
            points=float(snapshot.points),
            rating=snapshot.rating,
            wins=snapshot.wins,
            draws=snapshot.draws,
            losses=snapshot.losses,
            byes=snapshot.byes,
            games_played=snapshot.games_played,
            tournaments_played=snapshot.tournaments_played,
        )
        for snapshot, profile in result.all()
    ]
    return LeaderboardResponse(
        season=SeasonResponse.model_validate(season) if season else None,
        generated_at=generated_at,
        rows=rows,
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_default_public_leaderboard(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> LeaderboardResponse:
    active_season = await get_active_season(session)
    return await get_snapshot_leaderboard(session, season=active_season, limit=limit, offset=offset)


async def get_leaderboard_for_season(
    session: AsyncSession,
    season_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> LeaderboardResponse:
    season = await get_season(session, season_id)
    return await get_snapshot_leaderboard(session, season=season, limit=limit, offset=offset)


async def get_home_leaderboard_preview(
    session: AsyncSession,
    limit: int = 5,
) -> list[dict[str, Any]]:
    leaderboard = await get_default_public_leaderboard(session, limit=limit, offset=0)
    return [row.model_dump(mode="json") for row in leaderboard.rows]
