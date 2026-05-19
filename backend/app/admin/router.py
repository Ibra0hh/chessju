import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import AdminActionLogListResponse, AdminIdentityResponse, AuditLogFilters
from app.admin.services import list_admin_action_logs
from app.auth.dependencies import require_admin
from app.database import get_db_session
from app.users.models import User
from app.users.services import get_role_names_for_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminIdentityResponse)
async def admin_me(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminIdentityResponse:
    roles = await get_role_names_for_user(session, current_admin.id)
    return AdminIdentityResponse(
        id=current_admin.id,
        email=current_admin.email,
        roles=roles,
        username=current_admin.profile.username,
        full_name=current_admin.profile.full_name,
    )


@router.get("/audit-logs", response_model=AdminActionLogListResponse)
async def audit_logs(
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, min_length=1, max_length=100),
    entity_type: str | None = Query(default=None, min_length=1, max_length=100),
    admin_id: uuid.UUID | None = None,
) -> AdminActionLogListResponse:
    filters = AuditLogFilters(
        limit=limit,
        offset=offset,
        action=action,
        entity_type=entity_type,
        admin_id=admin_id,
    )
    return await list_admin_action_logs(session, filters)
