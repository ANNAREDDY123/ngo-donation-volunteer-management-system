
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.beneficiary import Beneficiary, BeneficiaryStatus
from app.models.budget import Budget
from app.models.campaign import Campaign, CampaignStatus
from app.models.donation import Donation, DonationStatus
from app.models.donor import Donor, DonorStatus
from app.models.expense import Expense
from app.models.impact import ProjectImpact
from app.models.inventory import InventoryItem
from app.models.project import Project, ProjectStatus
from app.models.volunteer import Volunteer, VolunteerStatus


def count_rows(db: Session, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    if conditions:
        query = query.where(*conditions)
    return int(db.scalar(query) or 0)


def sum_column(db: Session, model, column) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(column), 0))) or 0)


def get_dashboard_overview(db: Session) -> dict:
    """Aggregate operational data from the existing NGO modules."""

    completed_amount = db.scalar(
        select(func.coalesce(func.sum(Donation.amount), 0)).where(
            Donation.status == DonationStatus.COMPLETED
        )
    ) or 0

    total_expenses = sum_column(db, Expense, Expense.amount)
    total_budget = sum_column(db, Budget, Budget.allocated_amount)

    total_target = sum_column(db, ProjectImpact, ProjectImpact.target_value)
    total_achieved = sum_column(db, ProjectImpact, ProjectImpact.actual_value)

    impact_count = count_rows(db, ProjectImpact)
    progress = (
        round((total_achieved / total_target) * 100, 2)
        if total_target > 0
        else 0.0
    )

    total_inventory_quantity = sum_column(
        db, InventoryItem, InventoryItem.quantity
    )

    return {
        "donations": {
            "total_count": count_rows(db, Donation),
            "completed_count": count_rows(
                db, Donation, Donation.status == DonationStatus.COMPLETED
            ),
            "pending_count": count_rows(
                db, Donation, Donation.status == DonationStatus.PENDING
            ),
            "completed_amount": int(completed_amount),
        },
        "campaigns": {
            "total_count": count_rows(db, Campaign),
            "active_count": count_rows(
                db, Campaign, Campaign.status == CampaignStatus.ACTIVE
            ),
        },
        "donors": {
            "total_count": count_rows(db, Donor),
            "active_count": count_rows(
                db, Donor, Donor.status == DonorStatus.ACTIVE
            ),
        },
        "volunteers": {
            "total_count": count_rows(db, Volunteer),
            "active_count": count_rows(
                db, Volunteer, Volunteer.status == VolunteerStatus.ACTIVE
            ),
        },
        "projects": {
            "total_count": count_rows(db, Project),
            "active_count": count_rows(
                db, Project, Project.status == ProjectStatus.ACTIVE
            ),
            "completed_count": count_rows(
                db, Project, Project.status == ProjectStatus.COMPLETED
            ),
        },
        "finance": {
            "total_expenses": total_expenses,
            "total_budget_allocated": total_budget,
        },
        "beneficiaries": {
            "total_count": count_rows(db, Beneficiary),
            "active_count": count_rows(
                db, Beneficiary, Beneficiary.status == BeneficiaryStatus.ACTIVE
            ),
        },
        "impact": {
            "total_count": impact_count,
            "total_target": total_target,
            "total_achieved": total_achieved,
            "overall_progress_percentage": progress,
        },
        "inventory": {
            "item_count": count_rows(db, InventoryItem),
            "total_quantity": total_inventory_quantity,
        },
    }
