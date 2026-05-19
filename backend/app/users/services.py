import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import Role, UserRole
from app.users.models import Profile, User
from app.users.schemas import (
    CurrentUserResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)


def build_current_user_response(user: User, roles: list[str]) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        status=user.status,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        roles=roles,
        profile=ProfileResponse.model_validate(user.profile),
        preferences=PreferencesResponse.model_validate(user.preferences),
    )


async def get_user_with_profile(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.profile), selectinload(User.preferences))
    )
    return result.scalar_one_or_none()


async def get_role_names_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await session.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_current_user_response(
    session: AsyncSession, user_id: uuid.UUID
) -> CurrentUserResponse | None:
    user = await get_user_with_profile(session, user_id)
    if user is None:
        return None
    roles = await get_role_names_for_user(session, user_id)
    return build_current_user_response(user, roles)


async def update_profile(
    session: AsyncSession, user: User, payload: ProfileUpdateRequest
) -> ProfileResponse:
    profile = user.profile
    update_data = payload.model_dump(exclude_unset=True)

    if "username" in update_data and update_data["username"] != profile.username:
        existing = await session.execute(
            select(Profile).where(
                Profile.username == update_data["username"], Profile.user_id != user.id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already registered",
            )

    for field_name, value in update_data.items():
        setattr(profile, field_name, value)

    await session.commit()
    await session.refresh(profile)
    return ProfileResponse.model_validate(profile)


async def update_preferences(
    session: AsyncSession, user: User, payload: PreferencesUpdateRequest
) -> PreferencesResponse:
    preferences = user.preferences
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(preferences, field_name, value)

    await session.commit()
    await session.refresh(preferences)
    return PreferencesResponse.model_validate(preferences)
