
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.impact import ImpactStatus
from app.models.user import User, UserRole
from app.schemas.impact import ImpactCreate, ImpactResponse, ImpactUpdate
from app.services.impacts import (
    create_impact,
    delete_impact,
    get_impact,
    list_impacts,
    update_impact,
)

router = APIRouter(prefix="/impacts", tags=["Project Impact Tracking"])

IMPACT_STAFF = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "",
    response_model=ImpactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_impact_endpoint(
    payload: ImpactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*IMPACT_STAFF)),
):
    try:
        return create_impact(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[ImpactResponse])
def list_impacts_endpoint(
    project_id: int | None = Query(default=None, gt=0),
    beneficiary_id: int | None = Query(default=None, gt=0),
    metric_name: str | None = Query(default=None, max_length=150),
    impact_status: ImpactStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*IMPACT_STAFF)),
):
    return list_impacts(
        db,
        project_id=project_id,
        beneficiary_id=beneficiary_id,
        metric_name=metric_name,
        impact_status=impact_status,
        skip=skip,
        limit=limit,
    )


@router.get("/{impact_id}", response_model=ImpactResponse)
def get_impact_endpoint(
    impact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*IMPACT_STAFF)),
):
    try:
        return get_impact(db, impact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{impact_id}", response_model=ImpactResponse)
def update_impact_endpoint(
    impact_id: int,
    payload: ImpactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*IMPACT_STAFF)),
):
    try:
        return update_impact(db, impact_id, payload)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Impact record not found" else 400
        raise HTTPException(status_code=code, detail=message) from exc


@router.delete("/{impact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_impact_endpoint(
    impact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    try:
        delete_impact(db, impact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
