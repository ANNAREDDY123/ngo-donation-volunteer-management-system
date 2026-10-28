
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def stage_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    user_id: int | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add an audit entry to the current transaction without committing."""
    if not action.strip():
        raise ValueError("Audit action cannot be empty")

    if not entity_type.strip():
        raise ValueError("Entity type cannot be empty")

    log = AuditLog(
        user_id=user_id,
        action=action.strip().upper(),
        entity_type=entity_type.strip(),
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
        ip_address=ip_address,
    )

    db.add(log)
    return log


def record_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    user_id: int | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Create and commit a standalone audit entry."""
    log = stage_audit_log(
        db=db,
        action=action,
        entity_type=entity_type,
        user_id=user_id,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )

    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(
    db: Session,
    user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    """Retrieve audit logs with optional filters."""
    statement = select(AuditLog)

    if user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)

    if action:
        statement = statement.where(
            AuditLog.action == action.strip().upper()
        )

    if entity_type:
        statement = statement.where(
            AuditLog.entity_type == entity_type.strip()
        )

    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)

    if date_from:
        statement = statement.where(AuditLog.created_at >= date_from)

    if date_to:
        statement = statement.where(AuditLog.created_at <= date_to)

    statement = (
        statement
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())
