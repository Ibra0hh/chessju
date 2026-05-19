import uuid

from fastapi import HTTPException, status

from app.users.models import User


def ensure_self(user: User, target_user_id: uuid.UUID) -> None:
    if user.id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Object access denied")
