
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.donation import Donation, DonationStatus
from app.models.donor import Donor
from app.models.receipt import DonationReceipt
from app.models.user import User


def utc_now():
    return datetime.now(timezone.utc)


def generate_receipt_number(db: Session) -> str:
    """Generate a unique receipt identifier."""
    year = utc_now().year
    prefix = f"NGO-{year}-"

    latest = db.scalar(
        select(DonationReceipt.receipt_number)
        .where(DonationReceipt.receipt_number.like(f"{prefix}%"))
        .order_by(DonationReceipt.id.desc())
        .limit(1)
    )

    sequence = 1
    if latest:
        try:
            sequence = int(latest.rsplit("-", 1)[1]) + 1
        except (ValueError, IndexError):
            sequence = db.scalar(
                select(DonationReceipt.id).order_by(
                    DonationReceipt.id.desc()
                ).limit(1)
            ) or 0
            sequence += 1

    return f"{prefix}{sequence:06d}"


def issue_receipt(
    db: Session,
    donation_id: int,
    current_user: User,
) -> DonationReceipt:
    donation = db.get(Donation, donation_id)

    if donation is None:
        raise ValueError("Donation not found")

    if donation.status != DonationStatus.COMPLETED:
        raise ValueError("Receipts can only be issued for completed donations")

    existing = db.scalar(
        select(DonationReceipt).where(
            DonationReceipt.donation_id == donation_id
        )
    )
    if existing:
        raise ValueError("A receipt already exists for this donation")

    receipt = DonationReceipt(
        receipt_number=generate_receipt_number(db),
        donation_id=donation.id,
        amount=donation.amount,
        currency=donation.currency,
        issued_by=current_user.id,
    )

    db.add(receipt)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A receipt already exists or a receipt number conflict occurred"
        ) from exc

    db.refresh(receipt)
    return receipt


def get_receipt(db: Session, receipt_id: int) -> DonationReceipt:
    receipt = db.get(DonationReceipt, receipt_id)
    if receipt is None:
        raise ValueError("Receipt not found")
    return receipt


def list_receipts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[DonationReceipt]:
    return db.scalars(
        select(DonationReceipt)
        .order_by(DonationReceipt.issued_at.desc(), DonationReceipt.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()


def list_receipts_for_donor_email(
    db: Session,
    email: str,
    skip: int = 0,
    limit: int = 100,
) -> list[DonationReceipt]:
    """Find receipts for donors whose registered email matches the user."""
    query = (
        select(DonationReceipt)
        .join(Donation, Donation.id == DonationReceipt.donation_id)
        .join(Donor, Donor.id == Donation.donor_id)
        .where(Donor.email == email)
        .order_by(DonationReceipt.issued_at.desc(), DonationReceipt.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.scalars(query).all()
