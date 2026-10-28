
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.receipt import ReceiptIssue, ReceiptResponse
from app.services.receipts import (
    get_receipt,
    issue_receipt,
    list_receipts,
    list_receipts_for_donor_email,
)

router = APIRouter(prefix="/receipts", tags=["Donation Receipts"])

RECEIPT_STAFF = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_receipt_endpoint(
    payload: ReceiptIssue,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIPT_STAFF)),
):
    try:
        return issue_receipt(db, payload.donation_id, current_user)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Donation not found" else 400
        raise HTTPException(status_code=code, detail=message) from exc


@router.get("/mine", response_model=list[ReceiptResponse])
def list_my_receipts_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_receipts_for_donor_email(
        db,
        email=current_user.email,
        skip=skip,
        limit=limit,
    )


@router.get("", response_model=list[ReceiptResponse])
def list_receipts_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIPT_STAFF)),
):
    return list_receipts(db, skip=skip, limit=limit)


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt_endpoint(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*RECEIPT_STAFF)),
):
    try:
        return get_receipt(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
