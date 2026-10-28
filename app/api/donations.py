
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.donation import DonationStatus
from app.models.user import User, UserRole
from app.schemas.donation import (
    DonationCreate,
    DonationResponse,
    DonationUpdate,
)
from app.services.donations import (
    create_donation,
    get_donation,
    list_donations,
    update_donation,
)

router = APIRouter(prefix="/donations", tags=["Donation Management"])

DONATION_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=DonationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_donation_endpoint(
    data: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*DONATION_MANAGERS)),
):
    try:
        return create_donation(data, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A donation with this transaction reference already exists.",
        ) from exc


@router.get("", response_model=list[DonationResponse])
def list_donations_endpoint(
    donor_id: int | None = Query(default=None, gt=0),
    campaign_id: int | None = Query(default=None, gt=0),
    donation_status: DonationStatus | None = Query(
        default=None, alias="status"
    ),
    search: str | None = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_donations(
        db,
        donor_id=donor_id,
        campaign_id=campaign_id,
        donation_status=donation_status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{donation_id}", response_model=DonationResponse)
def get_donation_endpoint(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    donation = get_donation(donation_id, db)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return donation


@router.patch("/{donation_id}", response_model=DonationResponse)
def update_donation_endpoint(
    donation_id: int,
    data: DonationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*DONATION_MANAGERS)),
):
    donation = get_donation(donation_id, db)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")

    try:
        return update_donation(donation, data, db, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A donation with this transaction reference already exists.",
        ) from exc
