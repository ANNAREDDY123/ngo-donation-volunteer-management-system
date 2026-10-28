
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.assignment import AssignmentStatus
from app.models.user import User, UserRole
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
)
from app.services.assignments import (
    create_assignment,
    delete_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
    volunteer_owns_assignment,
)

router = APIRouter(prefix="/assignments", tags=["Volunteer Assignments"])

ASSIGNMENT_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_endpoint(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ASSIGNMENT_MANAGERS)),
):
    try:
        return create_assignment(data, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[AssignmentResponse])
def list_assignments_endpoint(
    volunteer_id: int | None = Query(default=None, gt=0),
    assignment_status: AssignmentStatus | None = Query(
        default=None, alias="status"
    ),
    search: str | None = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.VOLUNTEER:
        own_volunteer = next(
            (
                item
                for item in list_volunteers_for_user(current_user, db)
            ),
            None,
        )
        if own_volunteer is None:
            return []
        if volunteer_id is not None and volunteer_id != own_volunteer.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        volunteer_id = own_volunteer.id

    return list_assignments(
        db,
        volunteer_id=volunteer_id,
        assignment_status=assignment_status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = get_assignment(assignment_id, db)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if current_user.role == UserRole.VOLUNTEER:
        if not volunteer_owns_assignment(assignment, current_user, db):
            raise HTTPException(status_code=403, detail="Access denied.")

    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment_endpoint(
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ASSIGNMENT_MANAGERS)),
):
    assignment = get_assignment(assignment_id, db)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    try:
        return update_assignment(assignment, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ASSIGNMENT_MANAGERS)),
):
    assignment = get_assignment(assignment_id, db)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    try:
        delete_assignment(assignment, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def list_volunteers_for_user(user: User, db: Session):
    from sqlalchemy import select
    from app.models.volunteer import Volunteer

    return list(
        db.scalars(
            select(Volunteer).where(Volunteer.user_id == user.id)
        ).all()
    )
