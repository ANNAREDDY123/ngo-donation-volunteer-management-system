
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.project_approval import ApprovalStatus
from app.models.user import User, UserRole
from app.schemas.approval import (
    ApprovalDecision,
    ApprovalResponse,
    ApprovalSubmit,
)
from app.services.approvals import (
    decide_project_approval,
    list_project_approvals,
    submit_project_for_approval,
)

router = APIRouter(prefix="/approvals", tags=["Project Approvals"])


@router.post(
    "/projects/{project_id}/submit",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_project(
    project_id: int,
    payload: ApprovalSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.NGO_MANAGER)
    ),
):
    try:
        return submit_project_for_approval(
            db,
            project_id,
            current_user,
            payload.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}",
    response_model=list[ApprovalResponse],
)
def get_project_approval_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return list_project_approvals(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{approval_id}/decision",
    response_model=ApprovalResponse,
)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    try:
        return decide_project_approval(
            db,
            approval_id,
            current_user,
            payload.decision,
            payload.comments,
        )
    except ValueError as exc:
        message = str(exc)
        code = 404 if message in {
            "Approval request not found",
            "Project not found",
        } else 400
        raise HTTPException(status_code=code, detail=message) from exc
