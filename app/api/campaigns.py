
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.campaign import CampaignStatus
from app.models.user import User, UserRole
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.services.campaigns import (
    create_campaign,
    delete_campaign,
    get_campaign,
    list_campaigns,
    update_campaign,
)

router = APIRouter(prefix="/campaigns", tags=["Fundraising Campaigns"])

CAMPAIGN_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
)


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign_endpoint(
    data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CAMPAIGN_MANAGERS)),
):
    return create_campaign(data, current_user.id, db)


@router.get("", response_model=list[CampaignResponse])
def list_campaigns_endpoint(
    search: str | None = Query(default=None, max_length=200),
    campaign_status: CampaignStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_campaigns(
        db,
        search=search,
        status=campaign_status,
        skip=skip,
        limit=limit,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign_endpoint(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = get_campaign(campaign_id, db)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign_endpoint(
    campaign_id: int,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CAMPAIGN_MANAGERS)),
):
    campaign = get_campaign(campaign_id, db)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    try:
        return update_campaign(campaign, data, db, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_endpoint(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CAMPAIGN_MANAGERS)),
):
    campaign = get_campaign(campaign_id, db)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    try:
        delete_campaign(campaign, db, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
