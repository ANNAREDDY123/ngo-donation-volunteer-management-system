
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

DASHBOARD_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.get("/overview", response_model=DashboardResponse)
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*DASHBOARD_ROLES)),
):
    return get_dashboard_overview(db)
