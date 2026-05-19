import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.services import create_admin_action_log
from app.common.time import utc_now
from app.files.models import FileRecord
from app.games.models import Game
from app.tournaments.models import Pairing, Round, TimeControl, Tournament, TournamentRegistration
from app.tournaments.schemas import (
    AdminTournamentListResponse,
    AdminTournamentResponse,
    DeleteTournamentResponse,
    PairingBulkCreateRequest,
    PairingCreateRequest,
    PairingListResponse,
    PairingResponse,
    PairingUpdateRequest,
    PlayerSummaryResponse,
    ResultSubmitRequest,
    RoundCreateRequest,
    RoundDetailResponse,
    RoundListResponse,
    RoundResponse,
    RoundUpdateRequest,
    StandingRowResponse,
    StandingsResponse,
    TimeControlCreateRequest,
    TimeControlListResponse,
    TimeControlResponse,
    TimeControlUpdateRequest,
    TournamentCreateRequest,
    TournamentDetailResponse,
    TournamentListResponse,
    TournamentRegistrationListResponse,
    TournamentRegistrationResponse,
    TournamentRegistrationUpdateRequest,
    TournamentSummaryResponse,
    TournamentUpdateRequest,
    UserPairingListResponse,
    UserTournamentRegistrationListResponse,
    UserTournamentRegistrationResponse,
)
from app.users.models import Profile

SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
VISIBLE_TOURNAMENT_STATUSES = {
    "published",
    "registration_open",
    "registration_closed",
    "check_in",
    "in_progress",
    "completed",
    "cancelled",
}
HOME_TOURNAMENT_STATUSES = {
    "published",
    "registration_open",
    "registration_closed",
    "check_in",
}
REGISTERABLE_STATUS = "registration_open"
VISIBLE_ROUND_STATUSES = {"published", "in_progress", "completed", "cancelled"}
SCORING_RESULTS = {
    "white_win",
    "black_win",
    "draw",
    "white_forfeit",
    "black_forfeit",
    "double_forfeit",
    "bye",
}


def normalize_slug(value: str) -> str:
    slug = SLUG_NON_ALNUM.sub("-", value.lower()).strip("-")
    return slug or "tournament"


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _validate_status_filter(status_filter: str | None, allowed_statuses: set[str]) -> None:
    if status_filter is not None and status_filter not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status",
        )


async def _slug_exists(
    session: AsyncSession,
    slug: str,
    exclude_tournament_id: uuid.UUID | None = None,
) -> bool:
    statement = select(Tournament.id).where(Tournament.slug == slug)
    if exclude_tournament_id is not None:
        statement = statement.where(Tournament.id != exclude_tournament_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def _resolve_tournament_slug(
    session: AsyncSession,
    title: str,
    requested_slug: str | None = None,
    exclude_tournament_id: uuid.UUID | None = None,
) -> str:
    if requested_slug:
        slug = normalize_slug(requested_slug)
        if await _slug_exists(session, slug, exclude_tournament_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
        return slug

    base_slug = normalize_slug(title)
    candidate = base_slug
    suffix = 2
    while await _slug_exists(session, candidate, exclude_tournament_id):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


async def _validate_time_control(
    session: AsyncSession, time_control_id: uuid.UUID | None
) -> None:
    if time_control_id is None:
        return
    record = await session.get(TimeControl, time_control_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time control not found")


async def _validate_tournament_cover(
    session: AsyncSession, cover_file_id: uuid.UUID | None
) -> None:
    if cover_file_id is None:
        return
    record = await session.get(FileRecord, cover_file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover file not found")
    if record.file_type != "tournament_image":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cover file must be a tournament image",
        )


def _validate_tournament_dates(
    starts_at: datetime,
    ends_at: datetime | None,
    registration_close_at: datetime | None,
) -> None:
    if ends_at is not None and ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ends_at must be after starts_at",
        )
    if registration_close_at is not None and registration_close_at >= starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="registration_close_at must be before starts_at",
        )


def time_control_audit_snapshot(time_control: TimeControl) -> dict[str, Any]:
    return {
        "id": str(time_control.id),
        "name": time_control.name,
        "base_seconds": time_control.base_seconds,
        "increment_seconds": time_control.increment_seconds,
        "delay_seconds": time_control.delay_seconds,
        "type": time_control.type,
        "created_at": _dt(time_control.created_at),
        "updated_at": _dt(time_control.updated_at),
    }


def tournament_audit_snapshot(tournament: Tournament) -> dict[str, Any]:
    return {
        "id": str(tournament.id),
        "title": tournament.title,
        "slug": tournament.slug,
        "description": tournament.description,
        "status": tournament.status,
        "format": tournament.format,
        "time_control_id": str(tournament.time_control_id) if tournament.time_control_id else None,
        "max_players": tournament.max_players,
        "starts_at": _dt(tournament.starts_at),
        "ends_at": _dt(tournament.ends_at),
        "registration_open_at": _dt(tournament.registration_open_at),
        "registration_close_at": _dt(tournament.registration_close_at),
        "location": tournament.location,
        "created_by": str(tournament.created_by),
        "cover_file_id": str(tournament.cover_file_id) if tournament.cover_file_id else None,
        "created_at": _dt(tournament.created_at),
        "updated_at": _dt(tournament.updated_at),
        "deleted_at": _dt(tournament.deleted_at),
    }


def registration_audit_snapshot(registration: TournamentRegistration) -> dict[str, Any]:
    return {
        "id": str(registration.id),
        "tournament_id": str(registration.tournament_id),
        "user_id": str(registration.user_id),
        "status": registration.status,
        "seed_rating": registration.seed_rating,
        "checked_in_at": _dt(registration.checked_in_at),
        "created_at": _dt(registration.created_at),
        "updated_at": _dt(registration.updated_at),
        "cancelled_at": _dt(registration.cancelled_at),
    }


async def create_time_control(
    session: AsyncSession,
    admin_id: uuid.UUID,
    payload: TimeControlCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TimeControlResponse:
    time_control = TimeControl(**payload.model_dump())
    session.add(time_control)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="time_control.created",
        entity_type="time_control",
        entity_id=time_control.id,
        after=time_control_audit_snapshot(time_control),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(time_control)
    return TimeControlResponse.model_validate(time_control)


async def list_time_controls(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> TimeControlListResponse:
    total = await session.scalar(select(func.count()).select_from(TimeControl))
    result = await session.execute(
        select(TimeControl)
        .order_by(TimeControl.type.asc(), TimeControl.base_seconds.asc(), TimeControl.name.asc())
        .limit(limit)
        .offset(offset)
    )
    return TimeControlListResponse(
        items=[TimeControlResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def update_time_control(
    session: AsyncSession,
    admin_id: uuid.UUID,
    time_control_id: uuid.UUID,
    payload: TimeControlUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TimeControlResponse:
    time_control = await session.get(TimeControl, time_control_id)
    if time_control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time control not found")
    before = time_control_audit_snapshot(time_control)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(time_control, field_name, value)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="time_control.updated",
        entity_type="time_control",
        entity_id=time_control.id,
        before=before,
        after=time_control_audit_snapshot(time_control),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(time_control)
    return TimeControlResponse.model_validate(time_control)


async def _registration_counts(
    session: AsyncSession, tournament_id: uuid.UUID
) -> tuple[int, int]:
    approved_count = await session.scalar(
        select(func.count()).select_from(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.status == "approved",
        )
    )
    waitlisted_count = await session.scalar(
        select(func.count()).select_from(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.status == "waitlisted",
        )
    )
    return approved_count or 0, waitlisted_count or 0


async def _my_registration(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> TournamentRegistrationResponse | None:
    if user_id is None:
        return None
    result = await session.execute(
        select(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.user_id == user_id,
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        return None
    return TournamentRegistrationResponse.model_validate(registration)


async def build_tournament_summary(
    session: AsyncSession, tournament: Tournament
) -> TournamentSummaryResponse:
    approved_count, waitlisted_count = await _registration_counts(session, tournament.id)
    spots_remaining = None
    if tournament.max_players is not None:
        spots_remaining = max(tournament.max_players - approved_count, 0)
    return TournamentSummaryResponse(
        id=tournament.id,
        title=tournament.title,
        slug=tournament.slug,
        status=tournament.status,
        format=tournament.format,
        starts_at=tournament.starts_at,
        location=tournament.location,
        cover_file_id=tournament.cover_file_id,
        time_control=(
            TimeControlResponse.model_validate(tournament.time_control)
            if tournament.time_control
            else None
        ),
        max_players=tournament.max_players,
        approved_count=approved_count,
        waitlisted_count=waitlisted_count,
        spots_remaining=spots_remaining,
    )


async def build_tournament_detail(
    session: AsyncSession,
    tournament: Tournament,
    user_id: uuid.UUID | None = None,
) -> TournamentDetailResponse:
    summary = await build_tournament_summary(session, tournament)
    return TournamentDetailResponse(
        **summary.model_dump(),
        description=tournament.description,
        ends_at=tournament.ends_at,
        registration_open_at=tournament.registration_open_at,
        registration_close_at=tournament.registration_close_at,
        created_at=tournament.created_at,
        my_registration=await _my_registration(session, tournament.id, user_id),
    )


async def build_admin_tournament_response(
    session: AsyncSession,
    tournament: Tournament,
    user_id: uuid.UUID | None = None,
) -> AdminTournamentResponse:
    detail = await build_tournament_detail(session, tournament, user_id)
    return AdminTournamentResponse(
        **detail.model_dump(),
        created_by=tournament.created_by,
        updated_at=tournament.updated_at,
        deleted_at=tournament.deleted_at,
    )


def _tournament_with_time_control() -> Select[tuple[Tournament]]:
    return select(Tournament).options(selectinload(Tournament.time_control))


def _visible_tournaments_statement(status_filter: str | None = None) -> Select[tuple[Tournament]]:
    statement = _tournament_with_time_control().where(
        Tournament.deleted_at.is_(None),
        Tournament.status.in_(VISIBLE_TOURNAMENT_STATUSES),
    )
    if status_filter is not None:
        statement = statement.where(Tournament.status == status_filter)
    return statement


async def list_public_tournaments(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status_filter: str | None = None,
) -> TournamentListResponse:
    _validate_status_filter(status_filter, VISIBLE_TOURNAMENT_STATUSES)
    statement = _visible_tournaments_statement(status_filter)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Tournament.starts_at.asc(), Tournament.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tournaments = result.scalars().all()
    return TournamentListResponse(
        items=[await build_tournament_summary(session, tournament) for tournament in tournaments],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_home_upcoming_tournaments(
    session: AsyncSession, limit: int = 5
) -> list[dict[str, Any]]:
    now = utc_now()
    result = await session.execute(
        _tournament_with_time_control()
        .where(
            Tournament.deleted_at.is_(None),
            Tournament.status.in_(HOME_TOURNAMENT_STATUSES),
            Tournament.starts_at >= now,
        )
        .order_by(Tournament.starts_at.asc())
        .limit(limit)
    )
    summaries = [
        await build_tournament_summary(session, tournament) for tournament in result.scalars().all()
    ]
    return [summary.model_dump(mode="json") for summary in summaries]


async def get_public_tournament_by_slug(
    session: AsyncSession, slug: str, user_id: uuid.UUID | None = None
) -> TournamentDetailResponse:
    result = await session.execute(_visible_tournaments_statement().where(Tournament.slug == slug))
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return await build_tournament_detail(session, tournament, user_id)


async def create_tournament(
    session: AsyncSession,
    admin_id: uuid.UUID,
    payload: TournamentCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminTournamentResponse:
    await _validate_time_control(session, payload.time_control_id)
    await _validate_tournament_cover(session, payload.cover_file_id)
    slug = await _resolve_tournament_slug(session, payload.title, payload.slug)
    registration_open_at = payload.registration_open_at
    if payload.status == "registration_open" and registration_open_at is None:
        registration_open_at = utc_now()
    tournament = Tournament(
        title=payload.title,
        slug=slug,
        description=payload.description,
        status=payload.status,
        format=payload.format,
        time_control_id=payload.time_control_id,
        max_players=payload.max_players,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        registration_open_at=registration_open_at,
        registration_close_at=payload.registration_close_at,
        location=payload.location,
        created_by=admin_id,
        cover_file_id=payload.cover_file_id,
    )
    session.add(tournament)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="tournament.created",
        entity_type="tournament",
        entity_id=tournament.id,
        after=tournament_audit_snapshot(tournament),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(tournament, attribute_names=["time_control"])
    return await build_admin_tournament_response(session, tournament)


async def list_admin_tournaments(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    include_deleted: bool = False,
) -> AdminTournamentListResponse:
    statement = _tournament_with_time_control()
    if not include_deleted:
        statement = statement.where(Tournament.deleted_at.is_(None))
    if status_filter is not None:
        _validate_status_filter(
            status_filter,
            {
                "draft",
                "published",
                "registration_open",
                "registration_closed",
                "check_in",
                "in_progress",
                "completed",
                "cancelled",
            },
        )
        statement = statement.where(Tournament.status == status_filter)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Tournament.created_at.desc(), Tournament.id.desc())
        .limit(limit)
        .offset(offset)
    )
    tournaments = result.scalars().all()
    return AdminTournamentListResponse(
        items=[
            await build_admin_tournament_response(session, tournament) for tournament in tournaments
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_admin_tournament(session: AsyncSession, tournament_id: uuid.UUID) -> Tournament:
    result = await session.execute(
        _tournament_with_time_control().where(Tournament.id == tournament_id)
    )
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return tournament


def _ensure_tournament_mutable(tournament: Tournament) -> None:
    if tournament.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Soft-deleted tournaments cannot be changed",
        )


async def update_tournament(
    session: AsyncSession,
    admin_id: uuid.UUID,
    tournament_id: uuid.UUID,
    payload: TournamentUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminTournamentResponse:
    tournament = await get_admin_tournament(session, tournament_id)
    _ensure_tournament_mutable(tournament)
    before = tournament_audit_snapshot(tournament)
    update_data = payload.model_dump(exclude_unset=True)

    if "time_control_id" in update_data:
        await _validate_time_control(session, update_data["time_control_id"])
    if "cover_file_id" in update_data:
        await _validate_tournament_cover(session, update_data["cover_file_id"])
    if "slug" in update_data and update_data["slug"] is not None:
        update_data["slug"] = await _resolve_tournament_slug(
            session,
            title=tournament.title,
            requested_slug=update_data["slug"],
            exclude_tournament_id=tournament.id,
        )

    next_starts_at = update_data.get("starts_at", tournament.starts_at)
    next_ends_at = update_data.get("ends_at", tournament.ends_at)
    next_registration_close_at = update_data.get(
        "registration_close_at", tournament.registration_close_at
    )
    _validate_tournament_dates(next_starts_at, next_ends_at, next_registration_close_at)

    for field_name, value in update_data.items():
        setattr(tournament, field_name, value)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="tournament.updated",
        entity_type="tournament",
        entity_id=tournament.id,
        before=before,
        after=tournament_audit_snapshot(tournament),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(tournament, attribute_names=["time_control"])
    return await build_admin_tournament_response(session, tournament)


async def set_tournament_status(
    session: AsyncSession,
    admin_id: uuid.UUID,
    tournament_id: uuid.UUID,
    next_status: str,
    action: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminTournamentResponse:
    tournament = await get_admin_tournament(session, tournament_id)
    _ensure_tournament_mutable(tournament)
    if next_status == "published" and tournament.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft tournaments can be published",
        )
    if next_status == "registration_open" and tournament.status not in {
        "published",
        "registration_closed",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament cannot open registration from its current status",
        )
    if next_status == "registration_closed" and tournament.status != "registration_open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open registration can be closed",
        )
    if next_status == "cancelled" and tournament.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed tournaments cannot be cancelled",
        )

    before = tournament_audit_snapshot(tournament)
    tournament.status = next_status
    if next_status == "registration_open" and tournament.registration_open_at is None:
        tournament.registration_open_at = utc_now()
    if next_status == "registration_closed" and tournament.registration_close_at is None:
        tournament.registration_close_at = utc_now()

    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action=action,
        entity_type="tournament",
        entity_id=tournament.id,
        before=before,
        after=tournament_audit_snapshot(tournament),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(tournament, attribute_names=["time_control"])
    return await build_admin_tournament_response(session, tournament)


async def soft_delete_tournament(
    session: AsyncSession,
    admin_id: uuid.UUID,
    tournament_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DeleteTournamentResponse:
    tournament = await get_admin_tournament(session, tournament_id)
    before = tournament_audit_snapshot(tournament)
    if tournament.deleted_at is None:
        tournament.deleted_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="tournament.deleted",
        entity_type="tournament",
        entity_id=tournament.id,
        before=before,
        after=tournament_audit_snapshot(tournament),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    return DeleteTournamentResponse(deleted=True)


async def register_for_tournament(
    session: AsyncSession,
    user_id: uuid.UUID,
    tournament_id: uuid.UUID,
) -> TournamentRegistrationResponse:
    try:
        result = await session.execute(
            select(Tournament)
            .where(Tournament.id == tournament_id, Tournament.deleted_at.is_(None))
            .with_for_update()
        )
        tournament = result.scalar_one_or_none()
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )
        if tournament.status != REGISTERABLE_STATUS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tournament registration is not open",
            )
        existing = await session.execute(
            select(TournamentRegistration.id).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already registered for this tournament",
            )
        approved_count, _ = await _registration_counts(session, tournament_id)
        registration_status = "approved"
        if tournament.max_players is not None and approved_count >= tournament.max_players:
            registration_status = "waitlisted"
        registration = TournamentRegistration(
            tournament_id=tournament_id,
            user_id=user_id,
            status=registration_status,
        )
        session.add(registration)
        await session.commit()
        await session.refresh(registration)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already registered for this tournament",
        ) from exc

    return TournamentRegistrationResponse.model_validate(registration)


async def cancel_current_user_registration(
    session: AsyncSession,
    user_id: uuid.UUID,
    tournament_id: uuid.UUID,
) -> TournamentRegistrationResponse:
    result = await session.execute(
        select(TournamentRegistration)
        .join(Tournament)
        .where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.user_id == user_id,
        )
        .with_for_update()
        .options(selectinload(TournamentRegistration.tournament))
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found",
        )
    tournament = registration.tournament
    if tournament.starts_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel registration after tournament start",
        )
    if registration.status in {"cancelled", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration cannot be cancelled from its current status",
        )
    registration.status = "cancelled"
    registration.cancelled_at = utc_now()
    await session.commit()
    await session.refresh(registration)
    return TournamentRegistrationResponse.model_validate(registration)


async def list_user_tournament_registrations(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> UserTournamentRegistrationListResponse:
    base_statement = select(TournamentRegistration).where(
        TournamentRegistration.user_id == user_id
    )
    total = await session.scalar(select(func.count()).select_from(base_statement.subquery()))
    result = await session.execute(
        base_statement.options(
            selectinload(TournamentRegistration.tournament).selectinload(Tournament.time_control)
        )
        .order_by(TournamentRegistration.created_at.desc(), TournamentRegistration.id.desc())
        .limit(limit)
        .offset(offset)
    )
    registrations = result.scalars().all()
    items = [
        UserTournamentRegistrationResponse(
            registration=TournamentRegistrationResponse.model_validate(registration),
            tournament=await build_tournament_summary(session, registration.tournament),
        )
        for registration in registrations
    ]
    return UserTournamentRegistrationListResponse(
        items=items,
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_tournament_registrations(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
) -> TournamentRegistrationListResponse:
    await get_admin_tournament(session, tournament_id)
    allowed = {"pending", "approved", "waitlisted", "cancelled", "rejected"}
    _validate_status_filter(status_filter, allowed)
    statement = select(TournamentRegistration).where(
        TournamentRegistration.tournament_id == tournament_id
    )
    if status_filter is not None:
        statement = statement.where(TournamentRegistration.status == status_filter)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(TournamentRegistration.created_at.asc(), TournamentRegistration.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return TournamentRegistrationListResponse(
        items=[
            TournamentRegistrationResponse.model_validate(registration)
            for registration in result.scalars()
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def update_registration_status(
    session: AsyncSession,
    admin_id: uuid.UUID,
    registration_id: uuid.UUID,
    payload: TournamentRegistrationUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TournamentRegistrationResponse:
    registration = await session.get(TournamentRegistration, registration_id)
    if registration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found",
        )
    before = registration_audit_snapshot(registration)
    registration.status = payload.status
    registration.seed_rating = payload.seed_rating
    registration.checked_in_at = payload.checked_in_at
    if payload.status == "cancelled" and registration.cancelled_at is None:
        registration.cancelled_at = utc_now()
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="tournament_registration.updated",
        entity_type="tournament_registration",
        entity_id=registration.id,
        before=before,
        after=registration_audit_snapshot(registration),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(registration)
    return TournamentRegistrationResponse.model_validate(registration)


async def _profile_for_user(session: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def _player_summary(
    session: AsyncSession, user_id: uuid.UUID | None
) -> PlayerSummaryResponse | None:
    if user_id is None:
        return None
    profile = await _profile_for_user(session, user_id)
    if profile is None:
        return None
    return PlayerSummaryResponse(
        id=user_id,
        username=profile.username,
        full_name=profile.full_name,
    )


async def build_pairing_response(session: AsyncSession, pairing: Pairing) -> PairingResponse:
    return PairingResponse(
        id=pairing.id,
        round_id=pairing.round_id,
        tournament_id=pairing.tournament_id,
        board_number=pairing.board_number,
        white_user=await _player_summary(session, pairing.white_user_id),
        black_user=await _player_summary(session, pairing.black_user_id),
        status=pairing.status,
        result=pairing.result,
        result_reported_at=pairing.result_reported_at,
        created_at=pairing.created_at,
        updated_at=pairing.updated_at,
    )


async def get_visible_tournament_model_by_slug(session: AsyncSession, slug: str) -> Tournament:
    result = await session.execute(_visible_tournaments_statement().where(Tournament.slug == slug))
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return tournament


def round_audit_snapshot(round_record: Round) -> dict[str, Any]:
    return {
        "id": str(round_record.id),
        "tournament_id": str(round_record.tournament_id),
        "round_number": round_record.round_number,
        "title": round_record.title,
        "status": round_record.status,
        "starts_at": _dt(round_record.starts_at),
        "created_at": _dt(round_record.created_at),
        "updated_at": _dt(round_record.updated_at),
    }


def pairing_audit_snapshot(pairing: Pairing) -> dict[str, Any]:
    return {
        "id": str(pairing.id),
        "round_id": str(pairing.round_id),
        "tournament_id": str(pairing.tournament_id),
        "board_number": pairing.board_number,
        "white_user_id": str(pairing.white_user_id) if pairing.white_user_id else None,
        "black_user_id": str(pairing.black_user_id) if pairing.black_user_id else None,
        "status": pairing.status,
        "result": pairing.result,
        "result_reported_by": (
            str(pairing.result_reported_by) if pairing.result_reported_by else None
        ),
        "result_reported_at": _dt(pairing.result_reported_at),
        "created_at": _dt(pairing.created_at),
        "updated_at": _dt(pairing.updated_at),
    }


async def _next_round_number(session: AsyncSession, tournament_id: uuid.UUID) -> int:
    current = await session.scalar(
        select(func.max(Round.round_number)).where(Round.tournament_id == tournament_id)
    )
    return (current or 0) + 1


async def _next_board_number(session: AsyncSession, round_id: uuid.UUID) -> int:
    current = await session.scalar(
        select(func.max(Pairing.board_number)).where(Pairing.round_id == round_id)
    )
    return (current or 0) + 1


async def create_round(
    session: AsyncSession,
    admin_id: uuid.UUID,
    tournament_id: uuid.UUID,
    payload: RoundCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RoundResponse:
    tournament = await get_admin_tournament(session, tournament_id)
    if tournament.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is deleted")
    round_number = payload.round_number or await _next_round_number(session, tournament_id)
    round_record = Round(
        tournament_id=tournament_id,
        round_number=round_number,
        title=payload.title,
        status="draft",
        starts_at=payload.starts_at,
    )
    session.add(round_record)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Round number already exists for this tournament",
        ) from exc
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="round.created",
        entity_type="round",
        entity_id=round_record.id,
        after=round_audit_snapshot(round_record),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(round_record)
    return RoundResponse.model_validate(round_record)


async def list_admin_rounds(
    session: AsyncSession, tournament_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> RoundListResponse:
    await get_admin_tournament(session, tournament_id)
    statement = select(Round).where(Round.tournament_id == tournament_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Round.round_number.asc()).limit(limit).offset(offset)
    )
    return RoundListResponse(
        items=[RoundResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_public_rounds_by_slug(
    session: AsyncSession, slug: str, limit: int = 50, offset: int = 0
) -> RoundListResponse:
    tournament = await get_visible_tournament_model_by_slug(session, slug)
    statement = select(Round).where(
        Round.tournament_id == tournament.id,
        Round.status.in_(VISIBLE_ROUND_STATUSES),
    )
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Round.round_number.asc()).limit(limit).offset(offset)
    )
    return RoundListResponse(
        items=[RoundResponse.model_validate(item) for item in result.scalars()],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def get_admin_round(session: AsyncSession, round_id: uuid.UUID) -> Round:
    round_record = await session.get(Round, round_id)
    if round_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")
    return round_record


async def update_round(
    session: AsyncSession,
    admin_id: uuid.UUID,
    round_id: uuid.UUID,
    payload: RoundUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RoundResponse:
    round_record = await get_admin_round(session, round_id)
    before = round_audit_snapshot(round_record)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(round_record, field_name, value)
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="round.updated",
        entity_type="round",
        entity_id=round_record.id,
        before=before,
        after=round_audit_snapshot(round_record),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(round_record)
    return RoundResponse.model_validate(round_record)


async def set_round_status(
    session: AsyncSession,
    admin_id: uuid.UUID,
    round_id: uuid.UUID,
    next_status: str,
    action: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RoundResponse:
    round_record = await get_admin_round(session, round_id)
    before = round_audit_snapshot(round_record)
    round_record.status = next_status
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action=action,
        entity_type="round",
        entity_id=round_record.id,
        before=before,
        after=round_audit_snapshot(round_record),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(round_record)
    return RoundResponse.model_validate(round_record)


async def _round_detail(session: AsyncSession, round_record: Round) -> RoundDetailResponse:
    result = await session.execute(
        select(Pairing)
        .where(Pairing.round_id == round_record.id)
        .order_by(Pairing.board_number.asc())
    )
    pairings = [await build_pairing_response(session, pairing) for pairing in result.scalars()]
    return RoundDetailResponse(
        **RoundResponse.model_validate(round_record).model_dump(),
        pairings=pairings,
    )


async def get_admin_round_detail(session: AsyncSession, round_id: uuid.UUID) -> RoundDetailResponse:
    return await _round_detail(session, await get_admin_round(session, round_id))


async def get_public_round_detail(
    session: AsyncSession, slug: str, round_number: int
) -> RoundDetailResponse:
    tournament = await get_visible_tournament_model_by_slug(session, slug)
    result = await session.execute(
        select(Round).where(
            Round.tournament_id == tournament.id,
            Round.round_number == round_number,
            Round.status.in_(VISIBLE_ROUND_STATUSES),
        )
    )
    round_record = result.scalar_one_or_none()
    if round_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")
    return await _round_detail(session, round_record)


async def _approved_registrant_ids(
    session: AsyncSession, tournament_id: uuid.UUID
) -> set[uuid.UUID]:
    result = await session.execute(
        select(TournamentRegistration.user_id).where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.status == "approved",
        )
    )
    return set(result.scalars().all())


async def _players_already_paired(
    session: AsyncSession, round_id: uuid.UUID, exclude_pairing_id: uuid.UUID | None = None
) -> set[uuid.UUID]:
    statement = select(Pairing.white_user_id, Pairing.black_user_id).where(
        Pairing.round_id == round_id,
        Pairing.status != "cancelled",
    )
    if exclude_pairing_id is not None:
        statement = statement.where(Pairing.id != exclude_pairing_id)
    result = await session.execute(statement)
    players: set[uuid.UUID] = set()
    for white_user_id, black_user_id in result.all():
        if white_user_id:
            players.add(white_user_id)
        if black_user_id:
            players.add(black_user_id)
    return players


def _request_player_ids(payload: PairingCreateRequest | PairingUpdateRequest) -> list[uuid.UUID]:
    return [user_id for user_id in (payload.white_user_id, payload.black_user_id) if user_id]


def _is_bye_pairing(white_user_id: uuid.UUID | None, black_user_id: uuid.UUID | None) -> bool:
    return (white_user_id is None) != (black_user_id is None)


def _validate_pairing_shape(
    white_user_id: uuid.UUID | None,
    black_user_id: uuid.UUID | None,
    result: str = "pending",
) -> None:
    if white_user_id is not None and white_user_id == black_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="white_user_id and black_user_id cannot be the same",
        )
    is_bye = _is_bye_pairing(white_user_id, black_user_id)
    if is_bye:
        if result not in {"pending", "bye"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bye pairings can only use pending or bye result",
            )
        return
    if white_user_id is None or black_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Normal pairings require white_user_id and black_user_id",
        )
    if result == "bye":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bye result requires exactly one player",
        )


async def _validate_pairing_players(
    session: AsyncSession,
    tournament_id: uuid.UUID,
    round_id: uuid.UUID,
    player_ids: list[uuid.UUID],
    exclude_pairing_id: uuid.UUID | None = None,
) -> None:
    approved_ids = await _approved_registrant_ids(session, tournament_id)
    missing = set(player_ids) - approved_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pairing players must be approved tournament registrants",
        )
    already_paired = await _players_already_paired(session, round_id, exclude_pairing_id)
    conflicts = set(player_ids) & already_paired
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Player is already paired in this round",
        )


def _ensure_pairing_allowed_for_tournament(tournament: Tournament) -> None:
    if tournament.deleted_at is not None or tournament.status in {"cancelled", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create pairings for this tournament",
        )


async def create_pairing(
    session: AsyncSession,
    admin_id: uuid.UUID,
    round_id: uuid.UUID,
    payload: PairingCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
    audit_action: str = "pairing.created",
    commit: bool = True,
) -> PairingResponse:
    round_record = await get_admin_round(session, round_id)
    tournament = await get_admin_tournament(session, round_record.tournament_id)
    _ensure_pairing_allowed_for_tournament(tournament)
    board_number = payload.board_number or await _next_board_number(session, round_id)
    _validate_pairing_shape(payload.white_user_id, payload.black_user_id, payload.result)
    await _validate_pairing_players(
        session,
        tournament_id=round_record.tournament_id,
        round_id=round_id,
        player_ids=_request_player_ids(payload),
    )
    pairing = Pairing(
        round_id=round_id,
        tournament_id=round_record.tournament_id,
        board_number=board_number,
        white_user_id=payload.white_user_id,
        black_user_id=payload.black_user_id,
        result=payload.result,
        status="completed" if payload.result == "bye" else "scheduled",
        result_reported_by=admin_id if payload.result == "bye" else None,
        result_reported_at=utc_now() if payload.result == "bye" else None,
    )
    session.add(pairing)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Board number already exists for this round",
        ) from exc
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action=audit_action,
        entity_type="pairing",
        entity_id=pairing.id,
        after=pairing_audit_snapshot(pairing),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if payload.result == "bye":
        await _upsert_game_for_pairing(session, pairing)
    if commit:
        await session.commit()
        await session.refresh(pairing)
    return await build_pairing_response(session, pairing)


async def bulk_create_pairings(
    session: AsyncSession,
    admin_id: uuid.UUID,
    round_id: uuid.UUID,
    payload: PairingBulkCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PairingListResponse:
    board_numbers = [item.board_number for item in payload.pairings if item.board_number]
    if len(board_numbers) != len(set(board_numbers)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate board numbers in bulk pairing request",
        )
    players: list[uuid.UUID] = []
    for item in payload.pairings:
        _validate_pairing_shape(item.white_user_id, item.black_user_id, item.result)
        players.extend(_request_player_ids(item))
    if len(players) != len(set(players)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate players in bulk pairing request",
        )

    responses: list[PairingResponse] = []
    try:
        for item in payload.pairings:
            response = await create_pairing(
                session=session,
                admin_id=admin_id,
                round_id=round_id,
                payload=item,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_action="pairings.bulk_created",
                commit=False,
            )
            responses.append(response)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return PairingListResponse(
        items=responses,
        limit=len(responses),
        offset=0,
        total=len(responses),
    )


async def list_pairings_for_round(
    session: AsyncSession, round_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> PairingListResponse:
    await get_admin_round(session, round_id)
    statement = select(Pairing).where(Pairing.round_id == round_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Pairing.board_number.asc()).limit(limit).offset(offset)
    )
    pairings = result.scalars().all()
    return PairingListResponse(
        items=[await build_pairing_response(session, pairing) for pairing in pairings],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def list_public_pairings_by_slug(
    session: AsyncSession,
    slug: str,
    limit: int = 100,
    offset: int = 0,
    round_number: int | None = None,
) -> PairingListResponse:
    tournament = await get_visible_tournament_model_by_slug(session, slug)
    statement = select(Pairing).join(Round, Pairing.round_id == Round.id).where(
        Pairing.tournament_id == tournament.id,
        Round.status.in_(VISIBLE_ROUND_STATUSES),
    )
    if round_number is not None:
        statement = statement.where(Round.round_number == round_number)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Round.round_number.asc(), Pairing.board_number.asc())
        .limit(limit)
        .offset(offset)
    )
    pairings = result.scalars().all()
    return PairingListResponse(
        items=[await build_pairing_response(session, pairing) for pairing in pairings],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


async def update_pairing(
    session: AsyncSession,
    admin_id: uuid.UUID,
    pairing_id: uuid.UUID,
    payload: PairingUpdateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PairingResponse:
    pairing = await session.get(Pairing, pairing_id)
    if pairing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    if pairing.result != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update players or board after a result is submitted",
        )
    before = pairing_audit_snapshot(pairing)
    update_data = payload.model_dump(exclude_unset=True)
    next_white = update_data.get("white_user_id", pairing.white_user_id)
    next_black = update_data.get("black_user_id", pairing.black_user_id)
    _validate_pairing_shape(next_white, next_black, pairing.result)
    await _validate_pairing_players(
        session,
        tournament_id=pairing.tournament_id,
        round_id=pairing.round_id,
        player_ids=[user_id for user_id in (next_white, next_black) if user_id],
        exclude_pairing_id=pairing.id,
    )
    for field_name, value in update_data.items():
        setattr(pairing, field_name, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Board number already exists for this round",
        ) from exc
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="pairing.updated",
        entity_type="pairing",
        entity_id=pairing.id,
        before=before,
        after=pairing_audit_snapshot(pairing),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(pairing)
    return await build_pairing_response(session, pairing)


async def cancel_pairing(
    session: AsyncSession,
    admin_id: uuid.UUID,
    pairing_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PairingResponse:
    pairing = await session.get(Pairing, pairing_id)
    if pairing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    before = pairing_audit_snapshot(pairing)
    pairing.status = "cancelled"
    await session.flush()
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="pairing.cancelled",
        entity_type="pairing",
        entity_id=pairing.id,
        before=before,
        after=pairing_audit_snapshot(pairing),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(pairing)
    return await build_pairing_response(session, pairing)


def _validate_result_for_pairing(pairing: Pairing, result: str) -> None:
    is_bye = _is_bye_pairing(pairing.white_user_id, pairing.black_user_id)
    if pairing.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit result for cancelled pairing",
        )
    if is_bye and result not in {"pending", "bye"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bye pairing requires bye result",
        )
    if not is_bye and result == "bye":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bye result requires a bye pairing",
        )


async def _name_for_user(session: AsyncSession, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    profile = await _profile_for_user(session, user_id)
    return profile.full_name if profile else None


async def _upsert_game_for_pairing(session: AsyncSession, pairing: Pairing) -> Game | None:
    if pairing.result == "pending":
        return None
    result = await session.execute(select(Game).where(Game.pairing_id == pairing.id))
    game = result.scalar_one_or_none()
    if game is None:
        game = Game(pairing_id=pairing.id, source="tournament")
        session.add(game)
    game.tournament_id = pairing.tournament_id
    game.round_id = pairing.round_id
    game.white_user_id = pairing.white_user_id
    game.black_user_id = pairing.black_user_id
    game.white_name = await _name_for_user(session, pairing.white_user_id)
    game.black_name = await _name_for_user(session, pairing.black_user_id)
    game.result = pairing.result
    game.played_at = pairing.result_reported_at
    await session.flush()
    return game


async def submit_pairing_result(
    session: AsyncSession,
    admin_id: uuid.UUID,
    pairing_id: uuid.UUID,
    payload: ResultSubmitRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PairingResponse:
    pairing = await session.get(Pairing, pairing_id)
    if pairing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    _validate_result_for_pairing(pairing, payload.result)
    before = pairing_audit_snapshot(pairing)
    pairing.result = payload.result
    if payload.result == "pending":
        pairing.status = "scheduled"
        pairing.result_reported_by = None
        pairing.result_reported_at = None
    else:
        pairing.status = "completed"
        pairing.result_reported_by = admin_id
        pairing.result_reported_at = utc_now()
    await session.flush()
    await _upsert_game_for_pairing(session, pairing)
    await create_admin_action_log(
        db=session,
        admin_id=admin_id,
        action="pairing.result_submitted",
        entity_type="pairing",
        entity_id=pairing.id,
        before=before,
        after=pairing_audit_snapshot(pairing),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await session.commit()
    await session.refresh(pairing)
    return await build_pairing_response(session, pairing)


async def list_user_pairings(
    session: AsyncSession,
    user_id: uuid.UUID,
    tournament_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> UserPairingListResponse:
    statement = select(Pairing).where(
        or_(Pairing.white_user_id == user_id, Pairing.black_user_id == user_id)
    )
    if tournament_id is not None:
        statement = statement.where(Pairing.tournament_id == tournament_id)
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    result = await session.execute(
        statement.order_by(Pairing.created_at.desc(), Pairing.id.desc()).limit(limit).offset(offset)
    )
    pairings = result.scalars().all()
    return UserPairingListResponse(
        items=[await build_pairing_response(session, pairing) for pairing in pairings],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


def _empty_standing(user_id: uuid.UUID, profile: Profile) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "username": profile.username,
        "full_name": profile.full_name,
        "points": 0.0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "byes": 0,
        "games_played": 0,
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


async def compute_tournament_standings(
    session: AsyncSession, tournament_id: uuid.UUID
) -> StandingsResponse:
    await get_admin_tournament(session, tournament_id)
    registration_result = await session.execute(
        select(TournamentRegistration.user_id, Profile)
        .join(Profile, Profile.user_id == TournamentRegistration.user_id)
        .where(
            TournamentRegistration.tournament_id == tournament_id,
            TournamentRegistration.status == "approved",
        )
    )
    rows: dict[uuid.UUID, dict[str, Any]] = {
        user_id: _empty_standing(user_id, profile)
        for user_id, profile in registration_result.all()
    }
    pairing_result = await session.execute(
        select(Pairing).where(
            Pairing.tournament_id == tournament_id,
            Pairing.status == "completed",
            Pairing.result.in_(SCORING_RESULTS),
        )
    )
    for pairing in pairing_result.scalars():
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

    sorted_rows = sorted(
        rows.values(),
        key=lambda row: (-row["points"], -row["wins"], -row["draws"], row["username"]),
    )
    return StandingsResponse(
        tournament_id=tournament_id,
        items=[
            StandingRowResponse(rank=index + 1, **row)
            for index, row in enumerate(sorted_rows)
        ],
    )


async def compute_public_standings_by_slug(session: AsyncSession, slug: str) -> StandingsResponse:
    tournament = await get_visible_tournament_model_by_slug(session, slug)
    return await compute_tournament_standings(session, tournament.id)
