
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.models.donation import Donation, DonationStatus
from app.models.donor import Donor, DonorStatus
from app.schemas.donation import DonationCreate, DonationUpdate
from app.services.audit_logs import stage_audit_log


def create_donation(
    data: DonationCreate,
    created_by: int,
    db: Session,
) -> Donation:
    donor = db.get(Donor, data.donor_id)

    if donor is None:
        raise ValueError("Donor not found.")

    if donor.status != DonorStatus.ACTIVE:
        raise ValueError("Donor is not active.")

    campaign = db.get(Campaign, data.campaign_id)

    if campaign is None:
        raise ValueError("Campaign not found.")

    if campaign.status != CampaignStatus.ACTIVE:
        raise ValueError("Donations require an active campaign.")

    if campaign.currency != data.currency:
        raise ValueError(
            "Donation currency must match campaign currency."
        )

    donation = Donation(
        **data.model_dump(),
        created_by=created_by,
        status=DonationStatus.PENDING,
    )
    db.add(donation)
    db.flush()

    stage_audit_log(
        db,
        action="CREATE",
        entity_type="Donation",
        user_id=created_by,
        entity_id=donation.id,
        details={
            "amount": donation.amount,
            "currency": donation.currency,
            "campaign_id": donation.campaign_id,
        },
    )

    db.commit()
    db.refresh(donation)
    return donation


def get_donation(
    donation_id: int,
    db: Session,
) -> Donation | None:
    return db.get(Donation, donation_id)


def list_donations(
    db: Session,
    donor_id: int | None = None,
    campaign_id: int | None = None,
    donation_status: DonationStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Donation]:
    statement = select(Donation)

    if donor_id is not None:
        statement = statement.where(Donation.donor_id == donor_id)

    if campaign_id is not None:
        statement = statement.where(Donation.campaign_id == campaign_id)

    if donation_status is not None:
        statement = statement.where(Donation.status == donation_status)

    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Donation.transaction_reference.ilike(pattern),
                Donation.notes.ilike(pattern),
            )
        )

    statement = statement.order_by(Donation.id.desc())
    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def update_donation(
    donation: Donation,
    data: DonationUpdate,
    db: Session,
    actor_id: int | None = None,
) -> Donation:
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("At least one field must be provided.")

    current_status = donation.status
    new_status = changes.get("status")

    allowed_transitions = {
        DonationStatus.PLEDGED: {
            DonationStatus.PENDING,
            DonationStatus.COMPLETED,
            DonationStatus.FAILED,
        },
        DonationStatus.PENDING: {
            DonationStatus.COMPLETED,
            DonationStatus.FAILED,
        },
        DonationStatus.COMPLETED: {
            DonationStatus.REFUNDED,
        },
        DonationStatus.FAILED: set(),
        DonationStatus.REFUNDED: set(),
    }

    if new_status is not None and new_status != current_status:
        if new_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Cannot change donation status from "
                f"{current_status.value} to {new_status.value}."
            )

    changed_fields = []

    for field, value in changes.items():
        if getattr(donation, field) != value:
            setattr(donation, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return donation

    stage_audit_log(
        db,
        action="UPDATE",
        entity_type="Donation",
        user_id=actor_id,
        entity_id=donation.id,
        details={"changed_fields": changed_fields},
    )

    db.commit()
    db.refresh(donation)
    return donation
