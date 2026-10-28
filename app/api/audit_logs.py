from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.db.database import get_db
from app.models.user import UserRole
from app.schemas.audit_log import AuditLogRead
from app.services.audit_logs import get_audit_logs


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)

AUDIT_LOG_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.get("/", response_model=list[AuditLogRead])
def list_audit_logs(
    user_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, min_length=1, max_length=50),
    entity_type: str | None = Query(
        default=None, min_length=1, max_length=100
    ),
    entity_id: str | None = Query(default=None, max_length=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*AUDIT_LOG_ROLES)),
):
    if date_from and date_to and date_from > date_to:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail="date_from must be on or before date_to",
        )

    return get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )