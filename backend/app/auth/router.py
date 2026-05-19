from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.auth.services import login_user, refresh_tokens, register_user, revoke_refresh_token
from app.database import get_db_session
from app.users.models import User
from app.users.schemas import CurrentUserResponse
from app.users.services import get_current_user_response

router = APIRouter(tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await register_user(
        session=session,
        payload=payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await login_user(
        session=session,
        payload=payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    return await refresh_tokens(
        session=session,
        refresh_token=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LogoutResponse:
    revoked = await revoke_refresh_token(session, payload.refresh_token)
    return LogoutResponse(revoked=revoked)


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    response = await get_current_user_response(session, current_user.id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return response
