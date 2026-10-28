
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.volunteer import VolunteerStatus
from app.schemas.volunteer import (
    VolunteerCreate,
    VolunteerResponse,
    VolunteerUpdate,
)
from app.services.volunteers import (
    create_volunteer,
    delete_volunteer,
    get_volunteer,
    list_volunteers,
    update_volunteer,
)

router = APIRouter(prefix="/volunteers", tags=["Volunteer Management"])

VOLUNTEER_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "",
    response_model=VolunteerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_volunteer_endpoint(
    data: VolunteerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*VOLUNTEER_MANAGERS)),
):
    try:
        return create_volunteer(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A volunteer profile already exists for this account.",
        ) from exc


@router.get("", response_model=list[VolunteerResponse])
def list_volunteers_endpoint(
    search: str | None = Query(default=None, max_length=200),
    volunteer_status: VolunteerStatus | None = Query(
        default=None, alias="status"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_volunteers(
        db,
        search=search,
        volunteer_status=volunteer_status,
        skip=skip,
        limit=limit,
    )


@router.get("/{volunteer_id}", response_model=VolunteerResponse)
def get_volunteer_endpoint(
    volunteer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    volunteer = get_volunteer(volunteer_id, db)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found.")
    return volunteer


@router.patch("/{volunteer_id}", response_model=VolunteerResponse)
def update_volunteer_endpoint(
    volunteer_id: int,
    data: VolunteerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*VOLUNTEER_MANAGERS)),
):
    volunteer = get_volunteer(volunteer_id, db)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found.")

    try:
        return update_volunteer(volunteer, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/{volunteer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_volunteer_endpoint(
    volunteer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*VOLUNTEER_MANAGERS)),
):
    volunteer = get_volunteer(volunteer_id, db)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found.")

    delete_volunteer(volunteer, db)
