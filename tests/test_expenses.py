
from datetime import date

from app.models.audit_log import AuditLog
from app.models.project import Project, ProjectStatus
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


def setup_expense_context(client, db_session):
    manager = create_user(
        client,
        db_session,
        "expense.manager@example.com",
        UserRole.NGO_MANAGER,
    )

    project = Project(
        title="Community Food Project",
        description="Provide food support.",
        location="Hyderabad",
        start_date=date(2026, 11, 1),
        end_date=date(2027, 3, 31),
        status=ProjectStatus.ACTIVE,
        created_by=manager.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    return {
        "project_id": project.id,
        "user_id": manager.id,
        "headers": login(client, manager.email),
    }


def expense_payload(project_id):
    return {
        "project_id": project_id,
        "category": "food",
        "amount": 2500,
        "description": "Food supplies for beneficiaries",
        "expense_date": "2026-11-10",
        "receipt_reference": "RCPT-1001",
        "notes": "Purchased from local supplier",
    }


def create_expense(client, context):
    return client.post(
        "/expenses",
        json=expense_payload(context["project_id"]),
        headers=context["headers"],
    )


def test_create_expense(client, db_session):
    context = setup_expense_context(client, db_session)
    response = create_expense(client, context)

    assert response.status_code == 201
    assert response.json()["amount"] == 2500
    assert response.json()["category"] == "food"
    assert response.json()["created_by"] == context["user_id"]


def test_create_expense_requires_authentication(client, db_session):
    context = setup_expense_context(client, db_session)

    response = client.post(
        "/expenses",
        json=expense_payload(context["project_id"]),
    )

    assert response.status_code == 401


def test_donor_cannot_create_expense(client, db_session):
    context = setup_expense_context(client, db_session)
    donor = create_user(
        client,
        db_session,
        "expense.donor@example.com",
        UserRole.DONOR,
    )
    headers = login(client, donor.email)

    response = client.post(
        "/expenses",
        json=expense_payload(context["project_id"]),
        headers=headers,
    )

    assert response.status_code == 403


def test_expense_amount_must_be_positive(client, db_session):
    context = setup_expense_context(client, db_session)
    payload = expense_payload(context["project_id"])
    payload["amount"] = 0

    response = client.post(
        "/expenses",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_expense_project_must_exist(client, db_session):
    context = setup_expense_context(client, db_session)
    payload = expense_payload(999999)

    response = client.post(
        "/expenses",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Project not found"


def test_list_expenses(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)
    assert created.status_code == 201

    response = client.get("/expenses", headers=context["headers"])

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_expenses_by_project_and_category(client, db_session):
    context = setup_expense_context(client, db_session)
    create_expense(client, context)

    response = client.get(
        f"/expenses?project_id={context['project_id']}&category=food",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_expense(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)

    response = client.get(
        f"/expenses/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Food supplies for beneficiaries"


def test_update_expense(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)

    response = client.patch(
        f"/expenses/{created.json()['id']}",
        json={"amount": 3500, "notes": "Updated expense amount"},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["amount"] == 3500
    assert response.json()["notes"] == "Updated expense amount"


def test_update_expense_rejects_negative_amount(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)

    response = client.patch(
        f"/expenses/{created.json()['id']}",
        json={"amount": -100},
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_missing_expense_returns_404(client, db_session):
    context = setup_expense_context(client, db_session)

    response = client.get("/expenses/999999", headers=context["headers"])

    assert response.status_code == 404


def test_delete_expense_requires_finance_or_admin(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)

    response = client.delete(
        f"/expenses/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 403


def test_finance_officer_can_delete_expense(client, db_session):
    context = setup_expense_context(client, db_session)
    created = create_expense(client, context)

    finance = create_user(
        client,
        db_session,
        "expense.finance@example.com",
        UserRole.FINANCE_OFFICER,
    )
    headers = login(client, finance.email)

    response = client.delete(
        f"/expenses/{created.json()['id']}",
        headers=headers,
    )

    assert response.status_code == 204

    missing = client.get(
        f"/expenses/{created.json()['id']}",
        headers=headers,
    )
    assert missing.status_code == 404


def test_expense_date_range_validation(client, db_session):
    context = setup_expense_context(client, db_session)

    response = client.get(
        "/expenses?start_date=2026-12-01&end_date=2026-11-01",
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_expense_cannot_be_updated_for_completed_project(
    client, db_session
):
    context = setup_expense_context(client, db_session)

    created = create_expense(client, context)
    assert created.status_code == 201

    project = db_session.get(Project, context["project_id"])
    project.status = ProjectStatus.COMPLETED
    db_session.commit()

    response = client.patch(
        f"/expenses/{created.json()['id']}",
        json={"notes": "Attempted update"},
        headers=context["headers"],
    )

    assert response.status_code == 400


def test_rejected_expense_update_does_not_create_audit_log(
    client, db_session
):
    context = setup_expense_context(client, db_session)

    created = create_expense(client, context)
    assert created.status_code == 201

    expense_id = created.json()["id"]
    project = db_session.get(Project, context["project_id"])
    project.status = ProjectStatus.COMPLETED
    db_session.commit()

    before = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    response = client.patch(
        f"/expenses/{expense_id}",
        json={"notes": "Rejected update"},
        headers=context["headers"],
    )

    assert response.status_code == 400

    after = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    assert after == before


def test_expense_update_creates_exactly_one_audit_log(
    client, db_session
):
    context = setup_expense_context(client, db_session)

    created = create_expense(client, context)
    assert created.status_code == 201

    expense_id = created.json()["id"]

    before = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    response = client.patch(
        f"/expenses/{expense_id}",
        json={"notes": "Updated notes"},
        headers=context["headers"],
    )

    assert response.status_code == 200

    after = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    assert after == before + 1


def test_expense_noop_update_does_not_create_audit_log(
    client, db_session
):
    context = setup_expense_context(client, db_session)

    created = create_expense(client, context)
    assert created.status_code == 201

    expense_id = created.json()["id"]
    original_notes = created.json()["notes"]

    before = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    response = client.patch(
        f"/expenses/{expense_id}",
        json={"notes": original_notes},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["notes"] == original_notes

    after = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type.ilike("expense"),
            AuditLog.entity_id == str(expense_id),
        )
        .count()
    )

    assert after == before
