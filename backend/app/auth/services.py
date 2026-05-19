from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import MEMBER_ROLE
from app.auth.models import Role, UserRole
from app.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, TokenResponse
from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.common.time import utc_now
from app.config import get_settings
from app.notifications.models import NotificationPreference
from app.users.models import Profile, RefreshToken, User, UserPreferences
from app.users.services import (
    build_current_user_response,
    get_role_names_for_user,
    get_user_with_profile,
)


def _token_expiry_seconds() -> int:
    return get_settings().access_token_expire_minutes * 60


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def _get_profile_by_username(session: AsyncSession, username: str) -> Profile | None:
    result = await session.execute(select(Profile).where(Profile.username == username))
    return result.scalar_one_or_none()


async def _get_member_role(session: AsyncSession) -> Role:
    result = await session.execute(select(Role).where(Role.name == MEMBER_ROLE))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default member role is not configured",
        )
    return role


def _request_ip(client_host: str | None) -> str | None:
    return client_host[:64] if client_host else None


async def _create_refresh_token(
    session: AsyncSession,
    user: User,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, RefreshToken]:
    settings = get_settings()
    plain_token = generate_refresh_token()
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(plain_token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=_request_ip(ip_address),
    )
    session.add(token_record)
    await session.flush()
    return plain_token, token_record


async def _create_token_response(
    session: AsyncSession,
    user: User,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenResponse:
    roles = await get_role_names_for_user(session, user.id)
    refresh_token, _ = await _create_refresh_token(session, user, user_agent, ip_address)
    access_token = create_access_token(user.id, roles)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_token_expiry_seconds(),
    )


async def register_user(
    session: AsyncSession,
    payload: RegisterRequest,
    user_agent: str | None,
    ip_address: str | None,
) -> AuthResponse:
    email = str(payload.email).lower()

    if await _get_user_by_email(session, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        )

    if await _get_profile_by_username(session, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username is already registered"
        )

    try:
        member_role = await _get_member_role(session)
        user = User(email=email, password_hash=hash_password(payload.password))
        session.add(user)
        await session.flush()

        profile = Profile(
            user_id=user.id,
            username=payload.username,
            full_name=payload.full_name,
            university_id=payload.university_id,
            chesscom_username=payload.chesscom_username,
        )
        preferences = UserPreferences(user_id=user.id)
        notification_preferences = NotificationPreference(user_id=user.id)
        user_role = UserRole(user_id=user.id, role_id=member_role.id)
        session.add_all([profile, preferences, notification_preferences, user_role])
        await session.flush()

        tokens = await _create_token_response(session, user, user_agent, ip_address)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already registered",
        ) from exc

    created_user = await get_user_with_profile(session, user.id)
    if created_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed"
        )
    roles = await get_role_names_for_user(session, created_user.id)
    return AuthResponse(tokens=tokens, user=build_current_user_response(created_user, roles))


async def login_user(
    session: AsyncSession,
    payload: LoginRequest,
    user_agent: str | None,
    ip_address: str | None,
) -> AuthResponse:
    user = await _get_user_by_email(session, str(payload.email).lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if user.status != "active" or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active"
        )

    tokens = await _create_token_response(session, user, user_agent, ip_address)
    await session.commit()

    loaded_user = await get_user_with_profile(session, user.id)
    if loaded_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User lookup failed"
        )
    roles = await get_role_names_for_user(session, loaded_user.id)
    return AuthResponse(tokens=tokens, user=build_current_user_response(loaded_user, roles))


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenResponse:
    token_hash = hash_refresh_token(refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if (
        token_record is None
        or token_record.revoked_at is not None
        or token_record.expires_at <= utc_now()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = await get_user_with_profile(session, token_record.user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    roles = await get_role_names_for_user(session, user.id)
    new_refresh_token, new_token_record = await _create_refresh_token(
        session, user, user_agent, ip_address
    )
    token_record.revoked_at = utc_now()
    token_record.replaced_by_token_id = new_token_record.id

    access_token = create_access_token(user.id, roles)
    await session.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=_token_expiry_seconds(),
    )


async def revoke_refresh_token(session: AsyncSession, refresh_token: str) -> bool:
    token_hash = hash_refresh_token(refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if token_record is None:
        return False

    if token_record.revoked_at is None:
        token_record.revoked_at = utc_now()
        await session.commit()

    return True
