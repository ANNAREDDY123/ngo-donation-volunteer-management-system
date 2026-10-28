
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.services.audit_logs import stage_audit_log


def create_campaign(
    data: CampaignCreate,
    created_by: int,
    db: Session,
) -> Campaign:
    campaign = Campaign(
        **data.model_dump(),
        created_by=created_by,
        status=CampaignStatus.DRAFT,
    )
    db.add(campaign)
    db.flush()

    stage_audit_log(
        db,
        action="CREATE",
        entity_type="Campaign",
        user_id=created_by,
        entity_id=campaign.id,
        details={"title": campaign.title},
    )

    db.commit()
    db.refresh(campaign)
    return campaign


def get_campaign(
    campaign_id: int,
    db: Session,
) -> Campaign | None:
    return db.get(Campaign, campaign_id)


def list_campaigns(
    db: Session,
    search: str | None = None,
    status: CampaignStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Campaign]:
    statement = select(Campaign)

    if search:
        statement = statement.where(
            Campaign.title.ilike(f"%{search.strip()}%")
        )

    if status is not None:
        statement = statement.where(Campaign.status == status)

    statement = statement.order_by(Campaign.id.desc())
    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def update_campaign(
    campaign: Campaign,
    data: CampaignUpdate,
    db: Session,
    actor_id: int | None = None,
) -> Campaign:
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("At least one field must be provided.")

    if campaign.status in {
        CampaignStatus.COMPLETED,
        CampaignStatus.CANCELLED,
    }:
        raise ValueError(
            "Completed or cancelled campaigns cannot be edited."
        )

    proposed_start = changes.get("start_date", campaign.start_date)
    proposed_end = changes.get("end_date", campaign.end_date)

    if (
        proposed_start is not None
        and proposed_end is not None
        and proposed_end < proposed_start
    ):
        raise ValueError("End date cannot be before start date.")

    changed_fields = []

    for field, value in changes.items():
        if getattr(campaign, field) != value:
            setattr(campaign, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return campaign

    stage_audit_log(
        db,
        action="UPDATE",
        entity_type="Campaign",
        user_id=actor_id,
        entity_id=campaign.id,
        details={"changed_fields": changed_fields},
    )

    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(
    campaign: Campaign,
    db: Session,
    actor_id: int | None = None,
) -> None:
    if campaign.status != CampaignStatus.DRAFT:
        raise ValueError("Only draft campaigns can be deleted.")

    stage_audit_log(
        db,
        action="DELETE",
        entity_type="Campaign",
        user_id=actor_id,
        entity_id=campaign.id,
        details={"title": campaign.title},
    )

    db.delete(campaign)
    db.commit()

