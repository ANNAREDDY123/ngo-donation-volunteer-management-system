from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.donor import DonorStatus, DonorType
from app.models.user import User, UserRole
from app.schemas.donor import DonorCreate, DonorResponse, DonorUpdate
from app.services.donors import (
    create_donor,
    delete_donor,
    get_donor,
    list_donors,
    update_donor,
)

router = APIRouter(prefix="/donors", tags=["Donors"])

DONOR_ACCESS_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=DonorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_donor_endpoint(
    data: DonorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*DONOR_ACCESS_ROLES)),
):
    try:
        return create_donor(data, user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A donor with this email already exists.",
        )


@router.get("", response_model=list[DonorResponse])
def list_donors_endpoint(
    search: str | None = Query(default=None, max_length=150),
    donor_type: DonorType | None = None,
    donor_status: DonorStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*DONOR_ACCESS_ROLES)),
):
    return list_donors(
        db=db,
        search=search,
        donor_type=donor_type.value if donor_type else None,
        status=donor_status.value if donor_status else None,
        skip=skip,
        limit=limit,
    )


@router.get("/{donor_id}", response_model=DonorResponse)
def get_donor_endpoint(
    donor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*DONOR_ACCESS_ROLES)),
):
    donor = get_donor(donor_id, db)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found.")
    return donor


@router.patch("/{donor_id}", response_model=DonorResponse)
def update_donor_endpoint(
    donor_id: int,
    data: DonorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*DONOR_ACCESS_ROLES)),
):
    donor = get_donor(donor_id, db)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found.")

    try:
        return update_donor(donor, data, db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A donor with this email already exists.",
        )


@router.delete("/{donor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donor_endpoint(
    donor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*DONOR_ACCESS_ROLES)),
):
    donor = get_donor(donor_id, db)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found.")

    delete_donor(donor, db)