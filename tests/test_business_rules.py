
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.campaign import CampaignStatus
from app.models.donation import DonationStatus
from app.models.project import ProjectStatus
from app.schemas.campaign import CampaignUpdate
from app.schemas.donation import DonationUpdate
from app.schemas.project import ProjectUpdate


def test_campaign_update_schema_accepts_empty_payload():
    # Empty-payload rejection belongs to the service layer.
    assert CampaignUpdate.model_validate({}).model_dump(
        exclude_unset=True
    ) == {}


def test_project_update_schema_accepts_empty_payload():
    # Empty-payload rejection belongs to the service layer.
    assert ProjectUpdate.model_validate({}).model_dump(
        exclude_unset=True
    ) == {}


def test_donation_update_schema_accepts_empty_payload():
    # Empty-payload rejection belongs to the service layer.
    assert DonationUpdate.model_validate({}).model_dump(
        exclude_unset=True
    ) == {}


def test_campaign_terminal_status_values():
    assert CampaignStatus.COMPLETED.value == "completed"
    assert CampaignStatus.CANCELLED.value == "cancelled"


def test_project_terminal_status_values():
    assert ProjectStatus.COMPLETED.value == "completed"
    assert ProjectStatus.CANCELLED.value == "cancelled"


def test_donation_terminal_status_values():
    assert DonationStatus.FAILED.value == "failed"
    assert DonationStatus.REFUNDED.value == "refunded"


def test_campaign_update_rejects_reversed_dates():
    start = datetime.now(timezone.utc) + timedelta(days=20)
    end = start - timedelta(days=1)

    with pytest.raises(ValidationError):
        CampaignUpdate(start_date=start, end_date=end)


def test_project_update_rejects_reversed_dates():
    start = datetime.now(timezone.utc) + timedelta(days=20)
    end = start - timedelta(days=1)

    with pytest.raises(ValidationError):
        ProjectUpdate(start_date=start, end_date=end)
