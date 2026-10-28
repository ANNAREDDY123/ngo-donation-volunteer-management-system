
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.beneficiary import BeneficiaryCategory, BeneficiaryStatus
from app.models.user import User, UserRole
from app.schemas.beneficiary import (
    BeneficiaryCreate,
    BeneficiaryResponse,
    BeneficiaryUpdate,
)
from app.services.beneficiaries import (
    create_beneficiary,
    delete_beneficiary,
    get_beneficiary,
    list_beneficiaries,
    update_beneficiary,
)

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiary Management"])

BENEFICIARY_STAFF = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "",
    response_model=BeneficiaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_beneficiary_endpoint(
    payload: BeneficiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*BENEFICIARY_STAFF)),
):
    return create_beneficiary(db, payload, current_user)


@router.get("", response_model=list[BeneficiaryResponse])
def list_beneficiaries_endpoint(
    category: BeneficiaryCategory | None = None,
    beneficiary_status: BeneficiaryStatus | None = Query(
        default=None,
        alias="status",
    ),
    search: str | None = Query(default=None, max_length=150),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*BENEFICIARY_STAFF)),
):
    return list_beneficiaries(
        db,
        category=category,
        status=beneficiary_status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{beneficiary_id}", response_model=BeneficiaryResponse)
def get_beneficiary_endpoint(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*BENEFICIARY_STAFF)),
):
    try:
        return get_beneficiary(db, beneficiary_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{beneficiary_id}", response_model=BeneficiaryResponse)
def update_beneficiary_endpoint(
    beneficiary_id: int,
    payload: BeneficiaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*BENEFICIARY_STAFF)),
):
    try:
        return update_beneficiary(db, beneficiary_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/{beneficiary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_beneficiary_endpoint(
    beneficiary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    try:
        delete_beneficiary(db, beneficiary_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
