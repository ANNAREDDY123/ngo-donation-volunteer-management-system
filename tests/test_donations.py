
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.campaign import Campaign, CampaignStatus
from app.models.donation import Donation, DonationStatus
from app.models.donor import Donor, DonorStatus, DonorType
from app.models.user import User, UserRole


def setup_manager_and_records(client, db_session):
    email = "donation.manager@example.com"

    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Donation Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert registration.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = UserRole.NGO_MANAGER
    db_session.commit()

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "SecurePass123!",
        },
    )
    assert login.status_code == 200
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    donor = Donor(
        full_name="Test Donor",
        email="donation.donor@example.com",
        phone="9876543210",
        donor_type=DonorType.INDIVIDUAL,
        status=DonorStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(donor)
    db_session.flush()

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        title="Active Donation Campaign",
        description="A campaign used to test donation management.",
        goal_amount=100000,
        currency="INR",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        status=CampaignStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(donor)
    db_session.refresh(campaign)

    return headers, user, donor, campaign


def donation_payload(donor_id, campaign_id, reference=None):
    return {
        "donor_id": donor_id,
        "campaign_id": campaign_id,
        "amount": 1500,
        "currency": "INR",
        "payment_method": "upi",
        "transaction_reference": reference,
        "notes": "Test donation",
    }


def test_list_donations_requires_authentication(client):
    response = client.get("/donations")
    assert response.status_code == 401


def test_donor_cannot_create_donation(client, access_token):
    response = client.post(
        "/donations",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "donor_id": 1,
            "campaign_id": 1,
            "amount": 1000,
            "payment_method": "upi",
        },
    )
    assert response.status_code == 403


def test_create_donation_success(client, db_session):
    headers, user, donor, campaign = setup_manager_and_records(
        client, db_session
    )

    response = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id, "TXN-1001"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["donor_id"] == donor.id
    assert data["campaign_id"] == campaign.id
    assert data["amount"] == 1500
    assert data["status"] == "pending"
    assert data["created_by"] == user.id


def test_create_donation_rejects_nonpositive_amount(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    payload = donation_payload(donor.id, campaign.id)
    payload["amount"] = 0

    response = client.post("/donations", headers=headers, json=payload)
    assert response.status_code == 422


def test_create_donation_rejects_missing_donor(client, db_session):
    headers, _, _, campaign = setup_manager_and_records(
        client, db_session
    )

    response = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(99999, campaign.id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Donor not found."


def test_create_donation_rejects_missing_campaign(client, db_session):
    headers, _, donor, _ = setup_manager_and_records(client, db_session)

    response = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, 99999),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Campaign not found."


def test_create_donation_rejects_inactive_campaign(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    campaign.status = CampaignStatus.DRAFT
    db_session.commit()

    response = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert response.status_code == 400
    assert "active campaign" in response.json()["detail"]


def test_create_donation_rejects_duplicate_reference(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    payload = donation_payload(donor.id, campaign.id, "TXN-DUPLICATE")

    first = client.post("/donations", headers=headers, json=payload)
    assert first.status_code == 201

    second = client.post("/donations", headers=headers, json=payload)
    assert second.status_code == 409


def test_list_and_filter_donations(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id, "TXN-FILTER"),
    )
    assert created.status_code == 201

    response = client.get(
        "/donations",
        headers=headers,
        params={"donor_id": donor.id, "status": "pending"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["transaction_reference"] == "TXN-FILTER"


def test_get_donation_by_id(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert created.status_code == 201

    donation_id = created.json()["id"]
    response = client.get(
        f"/donations/{donation_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == donation_id


def test_get_missing_donation_returns_404(client, db_session):
    headers, _, _, _ = setup_manager_and_records(client, db_session)

    response = client.get("/donations/99999", headers=headers)
    assert response.status_code == 404


def test_update_pending_donation_to_completed(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert created.status_code == 201

    donation_id = created.json()["id"]
    response = client.patch(
        f"/donations/{donation_id}",
        headers=headers,
        json={"status": "completed", "transaction_reference": "TXN-PAID"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["transaction_reference"] == "TXN-PAID"


def test_completed_donation_cannot_be_marked_failed(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )
    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert created.status_code == 201

    donation = db_session.get(Donation, created.json()["id"])
    assert donation is not None
    donation.status = DonationStatus.COMPLETED
    db_session.commit()

    response = client.patch(
        f"/donations/{donation.id}",
        headers=headers,
        json={"status": "failed"},
    )

    assert response.status_code == 400
    assert db_session.get(Donation, donation.id).status == DonationStatus.COMPLETED



def test_failed_donation_cannot_be_completed(client, db_session):
    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )

    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert created.status_code == 201

    donation = db_session.get(Donation, created.json()["id"])
    donation.status = DonationStatus.FAILED
    db_session.commit()

    response = client.patch(
        f"/donations/{donation.id}",
        headers=headers,
        json={"status": "completed"},
    )

    assert response.status_code == 400
    db_session.refresh(donation)
    assert donation.status == DonationStatus.FAILED


def test_donation_noop_update_does_not_create_audit_log(
    client, db_session
):
    from app.models.audit_log import AuditLog

    headers, _, donor, campaign = setup_manager_and_records(
        client, db_session
    )

    created = client.post(
        "/donations",
        headers=headers,
        json=donation_payload(donor.id, campaign.id),
    )
    assert created.status_code == 201

    donation_id = created.json()["id"]
    donation = db_session.get(Donation, donation_id)

    before = db_session.query(AuditLog).filter(
        AuditLog.entity_type.ilike("donation"),
        AuditLog.entity_id == str(donation_id),
    ).count()

    response = client.patch(
        f"/donations/{donation_id}",
        headers=headers,
        json={"notes": donation.notes},
    )

    assert response.status_code == 200

    after = db_session.query(AuditLog).filter(
        AuditLog.entity_type.ilike("donation"),
        AuditLog.entity_id == str(donation_id),
    ).count()

    assert after == before

