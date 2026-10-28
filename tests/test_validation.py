
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.campaign import CampaignStatus
from app.models.donation import DonationStatus
from app.models.project import ProjectStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.schemas.donation import DonationCreate, DonationUpdate
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate


def future_dates():
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(days=30)
    return start, end


def valid_campaign_payload():
    start, end = future_dates()
    return {
        "title": "Community Education",
        "description": "Education support for children in need.",
        "goal_amount": 50000,
        "currency": "INR",
        "start_date": start,
        "end_date": end,
    }


def valid_project_payload():
    start, end = future_dates()
    return {
        "title": "Community Health",
        "description": "Health support for local communities.",
        "start_date": start,
        "end_date": end,
    }


def valid_donation_payload():
    return {
        "donor_id": 1,
        "campaign_id": 1,
        "amount": 1000,
        "currency": "INR",
        "payment_method": "upi",
    }


def valid_expense_payload():
    return {
        "project_id": 1,
        "category": "food",
        "amount": 1000,
        "description": "Food supplies for beneficiaries",
    }


@pytest.mark.parametrize("amount", [0, -1])
def test_donation_rejects_nonpositive_amount(amount):
    payload = valid_donation_payload()
    payload["amount"] = amount

    with pytest.raises(ValidationError):
        DonationCreate(**payload)


@pytest.mark.parametrize("amount", [0, -1])
def test_expense_rejects_nonpositive_amount(amount):
    payload = valid_expense_payload()
    payload["amount"] = amount

    with pytest.raises(ValidationError):
        ExpenseCreate(**payload)


@pytest.mark.parametrize("amount", [0, -1])
def test_campaign_rejects_nonpositive_goal(amount):
    payload = valid_campaign_payload()
    payload["goal_amount"] = amount

    with pytest.raises(ValidationError):
        CampaignCreate(**payload)


def test_campaign_rejects_end_before_start():
    payload = valid_campaign_payload()
    payload["end_date"] = payload["start_date"] - timedelta(days=1)

    with pytest.raises(ValidationError):
        CampaignCreate(**payload)


def test_project_rejects_end_before_start():
    payload = valid_project_payload()
    payload["end_date"] = payload["start_date"] - timedelta(days=1)

    with pytest.raises(ValidationError):
        ProjectCreate(**payload)


def test_campaign_update_rejects_reversed_dates_when_both_provided():
    start, end = future_dates()

    with pytest.raises(ValidationError):
        CampaignUpdate(start_date=end, end_date=start)


def test_project_update_rejects_reversed_dates_when_both_provided():
    start, end = future_dates()

    with pytest.raises(ValidationError):
        ProjectUpdate(start_date=end, end_date=start)


def test_donation_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        DonationUpdate(status="invalid_status")


def test_campaign_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        CampaignUpdate(status="invalid_status")


def test_project_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        ProjectUpdate(status="invalid_status")


def test_expense_update_rejects_nonpositive_amount():
    with pytest.raises(ValidationError):
        ExpenseUpdate(amount=0)


def test_expense_rejects_missing_project_id():
    payload = valid_expense_payload()
    payload["project_id"] = 0

    with pytest.raises(ValidationError):
        ExpenseCreate(**payload)


def test_donation_rejects_missing_donor_id():
    payload = valid_donation_payload()
    payload["donor_id"] = 0

    with pytest.raises(ValidationError):
        DonationCreate(**payload)


def test_donation_rejects_missing_campaign_id():
    payload = valid_donation_payload()
    payload["campaign_id"] = 0

    with pytest.raises(ValidationError):
        DonationCreate(**payload)


def test_campaign_rejects_invalid_currency():
    payload = valid_campaign_payload()
    payload["currency"] = "12A"

    with pytest.raises(ValidationError):
        CampaignCreate(**payload)


def test_donation_rejects_invalid_currency():
    payload = valid_donation_payload()
    payload["currency"] = "12A"

    with pytest.raises(ValidationError):
        DonationCreate(**payload)


def test_project_status_enum_contains_expected_terminal_states():
    assert ProjectStatus.COMPLETED.value == "completed"
    assert ProjectStatus.CANCELLED.value == "cancelled"


def test_campaign_status_enum_contains_expected_terminal_states():
    assert CampaignStatus.COMPLETED.value == "completed"
    assert CampaignStatus.CANCELLED.value == "cancelled"


def test_donation_status_enum_contains_refunded_state():
    assert DonationStatus.REFUNDED.value == "refunded"
