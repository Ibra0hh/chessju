import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import ADMIN_ROLE_NAMES
from app.auth.security import decode_access_token
from app.database import get_db_session
from app.users.models import User
from app.users.services import get_role_names_for_user, get_user_with_profile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_with_profile(session, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


require_authenticated_user = get_current_user


def require_roles(*allowed_roles: str) -> Callable[..., object]:
    async def dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        role_names = set(await get_role_names_for_user(session, user.id))
        if not role_names.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


require_admin = require_roles(*ADMIN_ROLE_NAMES)
