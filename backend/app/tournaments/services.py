import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.services import create_admin_action_log
from app.common.time import utc_now
from app.files.models import FileRecord
from app.tournaments.models import TimeControl, Tournament, TournamentRegistration
from app.tournaments.schemas import (
    AdminTournamentListResponse,
    AdminTournamentResponse,
    DeleteTournamentResponse,
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
    UserTournamentRegistrationListResponse,
    UserTournamentRegistrationResponse,
)

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
