import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminActionLog
from app.admin.schemas import AdminActionLogListResponse, AuditLogFilters

SENSITIVE_AUDIT_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "jwt",
    "jwt_secret",
    "jwt_secret_key",
    "password",
    "password_hash",
    "refresh_token",
    "refresh_tokens",
    "secret",
    "token",
    "token_hash",
}
REDACTED_VALUE = "[redacted]"


def sanitize_audit_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_AUDIT_KEYS:
                sanitized[key] = REDACTED_VALUE
            else:
                sanitized[key] = sanitize_audit_payload(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_audit_payload(item) for item in value]

    return value


async def create_admin_action_log(
    db: AsyncSession,
    admin_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminActionLog:
    log = AdminActionLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=sanitize_audit_payload(before) if before is not None else None,
        after=sanitize_audit_payload(after) if after is not None else None,
        ip_address=ip_address[:64] if ip_address else None,
        user_agent=user_agent[:1000] if user_agent else None,
    )
    db.add(log)
    await db.flush()
    return log


def _apply_filters(
    statement: Select[tuple[AdminActionLog]], filters: AuditLogFilters
) -> Select[tuple[AdminActionLog]]:
    if filters.action:
        statement = statement.where(AdminActionLog.action == filters.action)
    if filters.entity_type:
        statement = statement.where(AdminActionLog.entity_type == filters.entity_type)
    if filters.admin_id:
        statement = statement.where(AdminActionLog.admin_id == filters.admin_id)
    return statement


async def list_admin_action_logs(
    db: AsyncSession, filters: AuditLogFilters
) -> AdminActionLogListResponse:
    filtered_statement = _apply_filters(select(AdminActionLog), filters)
    count_statement = _apply_filters(select(func.count()).select_from(AdminActionLog), filters)

    total = await db.scalar(count_statement)
    result = await db.execute(
        filtered_statement.order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )

    return AdminActionLogListResponse(
        items=list(result.scalars().all()),
        limit=filters.limit,
        offset=filters.offset,
        total=total or 0,
    )
