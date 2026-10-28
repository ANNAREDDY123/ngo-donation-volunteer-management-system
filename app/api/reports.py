
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.db.database import get_db
from app.models.beneficiary import BeneficiaryCategory, BeneficiaryStatus
from app.models.campaign import CampaignStatus
from app.models.donation import DonationStatus
from app.models.expense import ExpenseCategory
from app.models.impact import ImpactStatus
from app.models.user import User, UserRole
from app.services.reports import (
    build_beneficiary_report,
    build_campaign_report,
    build_donation_report,
    build_expense_report,
    build_impact_report,
)

router = APIRouter(prefix="/reports", tags=["Reports & CSV Export"])

REPORT_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
    UserRole.VOLUNTEER_COORDINATOR,
)


def csv_response(content: str, filename: str) -> StreamingResponse:
    stream = BytesIO(content.encode("utf-8-sig"))
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from must be on or before date_to",
        )


@router.get("/donations.csv")
def donation_report(
    date_from: date | None = None,
    date_to: date | None = None,
    donation_status: DonationStatus | None = None,
    campaign_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
):
    validate_date_range(date_from, date_to)
    content = build_donation_report(
        db,
        date_from=date_from,
        date_to=date_to,
        donation_status=donation_status,
        campaign_id=campaign_id,
    )
    return csv_response(content, "donations_report.csv")


@router.get("/campaigns.csv")
def campaign_report(
    campaign_status: CampaignStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
):
    content = build_campaign_report(db, campaign_status=campaign_status)
    return csv_response(content, "campaigns_report.csv")


@router.get("/expenses.csv")
def expense_report(
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: int | None = Query(default=None, gt=0),
    category: ExpenseCategory | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
):
    validate_date_range(date_from, date_to)
    content = build_expense_report(
        db,
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        category=category,
    )
    return csv_response(content, "expenses_report.csv")


@router.get("/beneficiaries.csv")
def beneficiary_report(
    category: BeneficiaryCategory | None = None,
    beneficiary_status: BeneficiaryStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
):
    content = build_beneficiary_report(
        db,
        category=category,
        beneficiary_status=beneficiary_status,
    )
    return csv_response(content, "beneficiaries_report.csv")


@router.get("/impact.csv")
def impact_report(
    project_id: int | None = Query(default=None, gt=0),
    impact_status: ImpactStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
):
    content = build_impact_report(
        db,
        project_id=project_id,
        impact_status=impact_status,
    )
    return csv_response(content, "impact_report.csv")
