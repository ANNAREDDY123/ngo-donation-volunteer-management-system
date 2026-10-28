
import csv
from datetime import date
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.beneficiary import Beneficiary
from app.models.campaign import Campaign
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.expense import Expense
from app.models.impact import ProjectImpact
from app.models.project import Project


def safe_csv_value(value):
    """Reduce spreadsheet formula-injection risk for text fields."""
    if value is None:
        return ""
    if isinstance(value, (int, float, date)):
        return value

    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def make_csv(headers: list[str], rows: list[tuple]) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headers)

    for row in rows:
        writer.writerow([safe_csv_value(value) for value in row])

    return buffer.getvalue()


def build_donation_report(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    donation_status: str | None = None,
    campaign_id: int | None = None,
) -> str:
    query = (
        select(
            Donation.id,
            Donation.donation_date,
            Donor.full_name,
            Donor.email,
            Campaign.title,
            Donation.amount,
            Donation.currency,
            Donation.status,
            Donation.payment_method,
            Donation.transaction_reference,
        )
        .join(Donor, Donor.id == Donation.donor_id)
        .join(Campaign, Campaign.id == Donation.campaign_id)
    )

    if date_from:
        query = query.where(Donation.donation_date >= date_from)
    if date_to:
        query = query.where(Donation.donation_date <= date_to)
    if donation_status:
        query = query.where(Donation.status == donation_status)
    if campaign_id is not None:
        query = query.where(Donation.campaign_id == campaign_id)

    query = query.order_by(Donation.donation_date.desc(), Donation.id.desc())
    records = db.execute(query).all()

    return make_csv(
        [
            "Donation ID",
            "Donation Date",
            "Donor Name",
            "Donor Email",
            "Campaign",
            "Amount",
            "Currency",
            "Status",
            "Payment Method",
            "Transaction Reference",
        ],
        records,
    )


def build_campaign_report(
    db: Session,
    campaign_status: str | None = None,
) -> str:
    query = select(
        Campaign.id,
        Campaign.title,
        Campaign.description,
        Campaign.goal_amount,
        Campaign.currency,
        Campaign.start_date,
        Campaign.end_date,
        Campaign.status,
    )

    if campaign_status:
        query = query.where(Campaign.status == campaign_status)

    records = db.execute(
        query.order_by(Campaign.id.desc())
    ).all()

    return make_csv(
        [
            "Campaign ID",
            "Title",
            "Description",
            "Goal Amount",
            "Currency",
            "Start Date",
            "End Date",
            "Status",
        ],
        records,
    )


def build_expense_report(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: int | None = None,
    category: str | None = None,
) -> str:
    query = (
        select(
            Expense.id,
            Project.title,
            Expense.category,
            Expense.amount,
            Expense.description,
            Expense.expense_date,
            Expense.receipt_reference,
            Expense.notes,
        )
        .join(Project, Project.id == Expense.project_id)
    )

    if date_from:
        query = query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
    if project_id is not None:
        query = query.where(Expense.project_id == project_id)
    if category:
        query = query.where(Expense.category == category)

    records = db.execute(
        query.order_by(Expense.expense_date.desc(), Expense.id.desc())
    ).all()

    return make_csv(
        [
            "Expense ID",
            "Project",
            "Category",
            "Amount",
            "Description",
            "Expense Date",
            "Receipt Reference",
            "Notes",
        ],
        records,
    )


def build_beneficiary_report(
    db: Session,
    category: str | None = None,
    beneficiary_status: str | None = None,
) -> str:
    query = select(
        Beneficiary.id,
        Beneficiary.full_name,
        Beneficiary.category,
        Beneficiary.status,
        Beneficiary.phone,
        Beneficiary.email,
        Beneficiary.address,
        Beneficiary.household_size,
        Beneficiary.support_needs,
        Beneficiary.created_at,
    )

    if category:
        query = query.where(Beneficiary.category == category)
    if beneficiary_status:
        query = query.where(Beneficiary.status == beneficiary_status)

    records = db.execute(
        query.order_by(Beneficiary.id.desc())
    ).all()

    return make_csv(
        [
            "Beneficiary ID",
            "Full Name",
            "Category",
            "Status",
            "Phone",
            "Email",
            "Address",
            "Household Size",
            "Support Needs",
            "Created At",
        ],
        records,
    )


def build_impact_report(
    db: Session,
    project_id: int | None = None,
    impact_status: str | None = None,
) -> str:
    query = (
        select(
            ProjectImpact.id,
            Project.title,
            ProjectImpact.metric_name,
            ProjectImpact.description,
            ProjectImpact.unit,
            ProjectImpact.target_value,
            ProjectImpact.actual_value,
            ProjectImpact.status,
            ProjectImpact.created_at,
        )
        .join(Project, Project.id == ProjectImpact.project_id)
    )

    if project_id is not None:
        query = query.where(ProjectImpact.project_id == project_id)
    if impact_status:
        query = query.where(ProjectImpact.status == impact_status)

    records = db.execute(
        query.order_by(ProjectImpact.id.desc())
    ).all()

    headers = [
        "Impact ID",
        "Project",
        "Metric",
        "Description",
        "Unit",
        "Target",
        "Actual",
        "Progress Percentage",
        "Status",
        "Created At",
    ]

    rows = []
    for record in records:
        target = record.target_value or 0
        actual = record.actual_value or 0
        progress = round((actual / target) * 100, 2) if target else 0.0

        rows.append(
            (
                record.id,
                record.title,
                record.metric_name,
                record.description,
                record.unit,
                target,
                actual,
                progress,
                record.status,
                record.created_at,
            )
        )

    return make_csv(headers, rows)
