from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.services.audit_logs import record_audit_log


def setup_audit_user(client, db_session, role=UserRole.NGO_MANAGER):
    email = f"audit.{role.value.lower()}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Audit Test User",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == email).first()
    user.role = role
    db_session.commit()
    db_session.refresh(user)

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    return {"user": user, "headers": headers}


def test_audit_logs_require_authentication(client):
    response = client.get("/audit-logs/")
    assert response.status_code == 401


def test_donor_cannot_access_audit_logs(client, db_session):
    context = setup_audit_user(client, db_session, UserRole.DONOR)

    response = client.get(
        "/audit-logs/",
        headers=context["headers"],
    )

    assert response.status_code == 403


def test_manager_can_list_audit_logs(client, db_session):
    context = setup_audit_user(client, db_session)

    record_audit_log(
        db_session,
        action="CREATE",
        entity_type="Campaign",
        entity_id=123,
        user_id=context["user"].id,
        details={"title": "Community Support"},
    )

    response = client.get(
        "/audit-logs/",
        headers=context["headers"],
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["action"] == "CREATE"
    assert data[0]["entity_type"] == "Campaign"
    assert data[0]["entity_id"] == "123"
    assert data[0]["details"]["title"] == "Community Support"


def test_audit_log_records_user_and_timestamp(client, db_session):
    context = setup_audit_user(client, db_session)

    log = record_audit_log(
        db_session,
        action="UPDATE",
        entity_type="Project",
        entity_id=42,
        user_id=context["user"].id,
    )

    assert log.id is not None
    assert log.user_id == context["user"].id
    assert log.created_at is not None


def test_audit_action_is_normalized(client, db_session):
    context = setup_audit_user(client, db_session)

    log = record_audit_log(
        db_session,
        action=" create ",
        entity_type="Campaign",
        user_id=context["user"].id,
    )

    assert log.action == "CREATE"


def test_audit_log_rejects_empty_action(client, db_session):
    context = setup_audit_user(client, db_session)

    try:
        record_audit_log(
            db_session,
            action=" ",
            entity_type="Campaign",
            user_id=context["user"].id,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "action" in str(exc).lower()


def test_audit_log_rejects_empty_entity_type(client, db_session):
    context = setup_audit_user(client, db_session)

    try:
        record_audit_log(
            db_session,
            action="CREATE",
            entity_type=" ",
            user_id=context["user"].id,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "entity type" in str(exc).lower()


def test_audit_logs_can_be_filtered(client, db_session):
    context = setup_audit_user(client, db_session)
    user_id = context["user"].id

    record_audit_log(
        db_session,
        action="CREATE",
        entity_type="Campaign",
        entity_id=1,
        user_id=user_id,
    )
    record_audit_log(
        db_session,
        action="UPDATE",
        entity_type="Project",
        entity_id=2,
        user_id=user_id,
    )

    response = client.get(
        "/audit-logs/?action=CREATE&entity_type=Campaign",
        headers=context["headers"],
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["action"] == "CREATE"
    assert data[0]["entity_type"] == "Campaign"


def test_audit_log_pagination(client, db_session):
    context = setup_audit_user(client, db_session)

    for number in range(3):
        record_audit_log(
            db_session,
            action="CREATE",
            entity_type="Campaign",
            entity_id=number + 1,
            user_id=context["user"].id,
        )

    response = client.get(
        "/audit-logs/?skip=1&limit=1",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_invalid_audit_date_range_is_rejected(client, db_session):
    context = setup_audit_user(client, db_session)

    response = client.get(
        "/audit-logs/?date_from=2026-12-31T00:00:00&date_to=2026-01-01T00:00:00",
        headers=context["headers"],
    )

    assert response.status_code == 422



def test_audit_logs_have_no_update_or_delete_endpoints(client, db_session):
    context = setup_audit_user(client, db_session)

    record_audit_log(
        db_session,
        action="CREATE",
        entity_type="Campaign",
        entity_id=10,
        user_id=context["user"].id,
    )

    update_response = client.put(
        "/audit-logs/1",
        json={"action": "DELETE"},
        headers=context["headers"],
    )
    delete_response = client.delete(
        "/audit-logs/1",
        headers=context["headers"],
    )

    # Either status is acceptable when no modifying route exists.
    assert update_response.status_code in (404, 405)
    assert delete_response.status_code in (404, 405)

    # Verify that the original audit record remains unchanged.
    assert db_session.query(AuditLog).count() == 1

# ============================================================
# LEVEL 19.2 - AUTOMATIC AUDIT LOGGING TESTS
# ============================================================

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.campaign import Campaign, CampaignStatus
from app.models.donation import Donation
from app.models.donor import Donor, DonorStatus, DonorType
from app.models.project import Project
from app.models.user import User, UserRole


def automatic_audit_manager(client, db_session, email):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Automatic Audit Test Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None

    user.role = UserRole.NGO_MANAGER
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "SecurePass123!",
        },
    )
    assert login_response.status_code == 200

    return user, {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }


def automatic_audit_campaign_payload(title="Audit Test Campaign"):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(days=30)

    return {
        "title": title,
        "description": "Campaign for automatic audit testing.",
        "goal_amount": 50000,
        "currency": "INR",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def automatic_audit_project_payload(title="Audit Test Project"):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(days=60)

    return {
        "title": title,
        "description": "Project for automatic audit testing.",
        "location": "Hyderabad",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def assert_automatic_audit_log(
    db_session,
    user_id,
    action,
    entity_type,
    entity_id,
):
    log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            func.upper(AuditLog.action) == action.upper(),
            func.lower(AuditLog.entity_type) == entity_type.lower(),
            AuditLog.entity_id == str(entity_id),
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if log is None:
        existing_logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.entity_id == str(entity_id),
            )
            .all()
        )

        actual = [
            {
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
            }
            for item in existing_logs
        ]

        assert log is not None, (
            f"Missing audit log: {action} {entity_type} {entity_id}. "
            f"Matching records found: {actual}"
        )

    assert log.created_at is not None
    return log


def test_campaign_create_and_update_are_audited(client, db_session):
    user, headers = automatic_audit_manager(
        client, db_session, "audit.campaign.auto@example.com"
    )

    created = client.post(
        "/campaigns",
        headers=headers,
        json=automatic_audit_campaign_payload(),
    )
    assert created.status_code == 201

    campaign_id = created.json()["id"]

    create_log = assert_automatic_audit_log(
        db_session, user.id, "CREATE", "campaign", campaign_id
    )
    assert create_log.details is not None

    updated = client.patch(
        f"/campaigns/{campaign_id}",
        headers=headers,
        json={"title": "Updated Audit Test Campaign"},
    )
    assert updated.status_code == 200

    update_log = assert_automatic_audit_log(
        db_session, user.id, "UPDATE", "campaign", campaign_id
    )
    assert "title" in update_log.details["changed_fields"]


def test_donation_create_and_update_are_audited(client, db_session):
    user, headers = automatic_audit_manager(
        client, db_session, "audit.donation.auto@example.com"
    )

    donor = Donor(
        full_name="Audit Test Donor",
        email="audit.donor.auto@example.com",
        phone="9876543210",
        donor_type=DonorType.INDIVIDUAL,
        status=DonorStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(donor)
    db_session.flush()

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        title="Audit Donation Campaign",
        description="Active campaign for audit testing.",
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

    created = client.post(
        "/donations",
        headers=headers,
        json={
            "donor_id": donor.id,
            "campaign_id": campaign.id,
            "amount": 1500,
            "currency": "INR",
            "payment_method": "upi",
            "transaction_reference": "AUDIT-TXN-001",
            "notes": "Automatic audit test",
        },
    )
    assert created.status_code == 201

    donation_id = created.json()["id"]

    assert_automatic_audit_log(
        db_session, user.id, "CREATE", "donation", donation_id
    )

    updated = client.patch(
        f"/donations/{donation_id}",
        headers=headers,
        json={
            "status": "completed",
            "transaction_reference": "AUDIT-TXN-PAID",
        },
    )
    assert updated.status_code == 200

    update_log = assert_automatic_audit_log(
        db_session, user.id, "UPDATE", "donation", donation_id
    )
    assert "status" in update_log.details["changed_fields"]


def test_project_create_and_update_are_audited(client, db_session):
    user, headers = automatic_audit_manager(
        client, db_session, "audit.project.auto@example.com"
    )

    created = client.post(
        "/projects",
        headers=headers,
        json=automatic_audit_project_payload(),
    )
    assert created.status_code == 201

    project_id = created.json()["id"]

    assert_automatic_audit_log(
        db_session, user.id, "CREATE", "project", project_id
    )

    updated = client.patch(
        f"/projects/{project_id}",
        headers=headers,
        json={"title": "Updated Audit Test Project"},
    )
    assert updated.status_code == 200

    update_log = assert_automatic_audit_log(
        db_session, user.id, "UPDATE", "project", project_id
    )
    assert "title" in update_log.details["changed_fields"]


def test_expense_create_and_update_are_audited(client, db_session):
    user, headers = automatic_audit_manager(
        client, db_session, "audit.expense.auto@example.com"
    )

    project = Project(
        title="Audit Expense Project",
        description="Project for expense audit testing.",
        location="Hyderabad",
        start_date=datetime(2026, 11, 1).date(),
        end_date=datetime(2027, 3, 31).date(),
        status=__import__(
            "app.models.project", fromlist=["ProjectStatus"]
        ).ProjectStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    created = client.post(
        "/expenses",
        headers=headers,
        json={
            "project_id": project.id,
            "category": "food",
            "amount": 2500,
            "description": "Audit test food supplies",
            "expense_date": "2026-11-10",
            "receipt_reference": "AUDIT-RCPT-001",
            "notes": "Initial audit test expense",
        },
    )
    assert created.status_code == 201

    expense_id = created.json()["id"]

    assert_automatic_audit_log(
        db_session, user.id, "CREATE", "expense", expense_id
    )

    updated = client.patch(
        f"/expenses/{expense_id}",
        headers=headers,
        json={"amount": 3500, "notes": "Updated audit test expense"},
    )
    assert updated.status_code == 200

    update_log = assert_automatic_audit_log(
        db_session, user.id, "UPDATE", "expense", expense_id
    )
    assert "amount" in update_log.details["changed_fields"]
