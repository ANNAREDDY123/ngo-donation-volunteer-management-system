
from datetime import date

from app.models.campaign import Campaign, CampaignStatus
from app.models.donation import Donation, DonationStatus, PaymentMethod
from app.models.donor import Donor, DonorStatus, DonorType
from app.models.receipt import DonationReceipt
from app.models.user import User, UserRole


def create_user(client, db_session, email, role):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": email.split("@")[0].title(),
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == email).first()
    user.role = role
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_receipt_context(client, db_session, status=DonationStatus.COMPLETED):
    manager = create_user(
        client,
        db_session,
        "receipt.manager@example.com",
        UserRole.FINANCE_OFFICER,
    )

    donor = Donor(
        full_name="Receipt Test Donor",
        email="receipt.donor@example.com",
        phone="9876543210",
        donor_type=DonorType.INDIVIDUAL,
        status=DonorStatus.ACTIVE,
        created_by=manager.id,
    )
    db_session.add(donor)
    db_session.commit()
    db_session.refresh(donor)

    campaign = Campaign(
        title="Receipt Test Campaign",
        description="Campaign for receipt tests",
        goal_amount=100000,
        currency="INR",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
        status=CampaignStatus.ACTIVE,
        created_by=manager.id,
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    
    donation = Donation(
        donor_id=donor.id,
        campaign_id=campaign.id,
        amount=500,
        currency="INR",
        status=status,
        payment_method=PaymentMethod.UPI,
        transaction_reference="RECEIPT-TEST-001",
        notes="Receipt test donation",
        donation_date=date.today(),
        created_by=manager.id,
    )

    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    donor_user = create_user(
        client,
        db_session,
        "receipt.donor.user@example.com",
        UserRole.DONOR,
    )

    return {
        "manager": manager,
        "manager_headers": login(client, manager.email),
        "donor": donor,
        "donor_user": donor_user,
        "donor_headers": login(client, donor_user.email),
        "donation": donation,
    }


def issue_receipt(client, context):
    return client.post(
        "/receipts",
        json={"donation_id": context["donation"].id},
        headers=context["manager_headers"],
    )


def test_issue_receipt_for_completed_donation(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = issue_receipt(client, context)

    assert response.status_code == 201
    assert response.json()["donation_id"] == context["donation"].id
    assert response.json()["amount"] == 500
    assert response.json()["currency"] == "INR"
    assert response.json()["receipt_number"].startswith("NGO-")


def test_issue_receipt_requires_authentication(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = client.post(
        "/receipts",
        json={"donation_id": context["donation"].id},
    )

    assert response.status_code == 401


def test_donor_cannot_issue_receipt(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = client.post(
        "/receipts",
        json={"donation_id": context["donation"].id},
        headers=context["donor_headers"],
    )

    assert response.status_code == 403


def test_receipt_rejects_missing_donation(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = client.post(
        "/receipts",
        json={"donation_id": 999999},
        headers=context["manager_headers"],
    )

    assert response.status_code == 404


def test_receipt_requires_positive_donation_id(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = client.post(
        "/receipts",
        json={"donation_id": 0},
        headers=context["manager_headers"],
    )

    assert response.status_code == 422


def test_receipt_not_issued_for_incomplete_donation(client, db_session):
    context = setup_receipt_context(
        client,
        db_session,
        status=DonationStatus.PENDING,
    )

    response = issue_receipt(client, context)

    assert response.status_code == 400
    assert "completed donations" in response.json()["detail"]


def test_duplicate_receipt_is_rejected(client, db_session):
    context = setup_receipt_context(client, db_session)

    first = issue_receipt(client, context)
    second = issue_receipt(client, context)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]


def test_receipt_number_is_unique(client, db_session):
    context = setup_receipt_context(client, db_session)
    response = issue_receipt(client, context)

    assert response.status_code == 201

    receipts = db_session.query(DonationReceipt).all()
    numbers = [receipt.receipt_number for receipt in receipts]

    assert len(numbers) == len(set(numbers))


def test_list_receipts_requires_staff_role(client, db_session):
    context = setup_receipt_context(client, db_session)
    issue_receipt(client, context)

    response = client.get(
        "/receipts",
        headers=context["donor_headers"],
    )

    assert response.status_code == 403


def test_staff_can_list_receipts(client, db_session):
    context = setup_receipt_context(client, db_session)
    issue_receipt(client, context)

    response = client.get(
        "/receipts",
        headers=context["manager_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_staff_can_get_receipt_by_id(client, db_session):
    context = setup_receipt_context(client, db_session)
    created = issue_receipt(client, context)

    response = client.get(
        f"/receipts/{created.json()['id']}",
        headers=context["manager_headers"],
    )

    assert response.status_code == 200
    assert response.json()["receipt_number"] == created.json()["receipt_number"]


def test_missing_receipt_returns_404(client, db_session):
    context = setup_receipt_context(client, db_session)

    response = client.get(
        "/receipts/999999",
        headers=context["manager_headers"],
    )

    assert response.status_code == 404


def test_donor_can_list_own_receipts_by_email(client, db_session):
    context = setup_receipt_context(client, db_session)

    # Match the signed-in user's email to the donor record's email.
    context["donor_user"].email = context["donor"].email
    db_session.commit()

    context["donor_headers"] = login(client, context["donor"].email)
    issue_receipt(client, context)

    response = client.get(
        "/receipts/mine",
        headers=context["donor_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_donor_receipts_do_not_include_other_donors(client, db_session):
    context = setup_receipt_context(client, db_session)
    issue_receipt(client, context)

    response = client.get(
        "/receipts/mine",
        headers=context["donor_headers"],
    )

    assert response.status_code == 200
    assert response.json() == []


def test_receipt_amount_is_a_snapshot(client, db_session):
    context = setup_receipt_context(client, db_session)
    created = issue_receipt(client, context)

    context["donation"].amount = 750
    db_session.commit()

    receipt = db_session.get(DonationReceipt, created.json()["id"])
    assert receipt.amount == 500


def test_receipt_currency_is_preserved(client, db_session):
    context = setup_receipt_context(client, db_session)
    response = issue_receipt(client, context)

    assert response.status_code == 201
    assert response.json()["currency"] == "INR"
