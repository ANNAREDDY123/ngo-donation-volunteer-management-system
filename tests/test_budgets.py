
from datetime import date
from app.models.expense import ExpenseCategory
from app.models.budget import Budget
from app.models.expense import Expense
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


def setup_budget_context(client, db_session):
    manager = create_user(
        client,
        db_session,
        "budget.manager@example.com",
        UserRole.NGO_MANAGER,
    )

    project = Project(
        title="Community Support Project",
        description="Support local families.",
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


def budget_payload(project_id, category=ExpenseCategory.FOOD, amount=20000):
    return {
        "project_id": project_id,
        "category": category,
        "allocated_amount": amount,
    }


def create_budget(client, context, category=ExpenseCategory.FOOD, amount=20000):
    return client.post(
        "/budgets",
        json=budget_payload(context["project_id"], category, amount),
        headers=context["headers"],
    )


def test_create_budget(client, db_session):
    context = setup_budget_context(client, db_session)
    response = create_budget(client, context)

    assert response.status_code == 201
    assert response.json()["allocated_amount"] == 20000
    assert response.json()["spent_amount"] == 0
    assert response.json()["remaining_amount"] == 20000
    assert response.json()["utilization_percentage"] == 0


def test_create_budget_requires_authentication(client, db_session):
    context = setup_budget_context(client, db_session)

    response = client.post(
        "/budgets",
        json=budget_payload(context["project_id"]),
    )

    assert response.status_code == 401


def test_donor_cannot_create_budget(client, db_session):
    context = setup_budget_context(client, db_session)
    donor = create_user(
        client,
        db_session,
        "budget.donor@example.com",
        UserRole.DONOR,
    )

    response = client.post(
        "/budgets",
        json=budget_payload(context["project_id"]),
        headers=login(client, donor.email),
    )

    assert response.status_code == 403


def test_budget_amount_must_be_positive(client, db_session):
    context = setup_budget_context(client, db_session)

    response = create_budget(client, context, amount=0)

    assert response.status_code == 422


def test_budget_project_must_exist(client, db_session):
    context = setup_budget_context(client, db_session)

    response = client.post(
        "/budgets",
        json=budget_payload(999999),
        headers=context["headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Project not found"


def test_duplicate_project_category_budget_rejected(client, db_session):
    context = setup_budget_context(client, db_session)

    first = create_budget(client, context)
    second = create_budget(client, context)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]


def test_list_budgets_and_filter_by_category(client, db_session):
    context = setup_budget_context(client, db_session)
    create_budget(client, context, category="food")
    create_budget(client, context, category="transport")

    response = client.get(
        f"/budgets?project_id={context['project_id']}&category=food",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "food"


def test_get_budget(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    response = client.get(
        f"/budgets/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["allocated_amount"] == 20000


def test_update_budget(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    response = client.patch(
        f"/budgets/{created.json()['id']}",
        json={"allocated_amount": 30000},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["allocated_amount"] == 30000


def test_update_budget_cannot_go_below_recorded_expenses(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    expense = Expense(
        project_id=context["project_id"],
        category="food",
        amount=5000,
        description="Food supplies",
        expense_date=date(2026, 11, 10),
        created_by=context["user_id"],
    )
    db_session.add(expense)
    db_session.commit()

    response = client.patch(
        f"/budgets/{created.json()['id']}",
        json={"allocated_amount": 4000},
        headers=context["headers"],
    )

    assert response.status_code == 400
    assert "less than recorded spending" in response.json()["detail"]


def test_budget_calculates_spending_and_utilization(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context, amount=20000)

    expense = Expense(
        project_id=context["project_id"],
        category="food",
        amount=5000,
        description="Food supplies",
        expense_date=date(2026, 11, 10),
        created_by=context["user_id"],
    )
    db_session.add(expense)
    db_session.commit()

    response = client.get(
        f"/budgets/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["spent_amount"] == 5000
    assert response.json()["remaining_amount"] == 15000
    assert response.json()["utilization_percentage"] == 25.0


def test_missing_budget_returns_404(client, db_session):
    context = setup_budget_context(client, db_session)

    response = client.get("/budgets/999999", headers=context["headers"])

    assert response.status_code == 404


def test_delete_budget_requires_finance_or_admin(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    response = client.delete(
        f"/budgets/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 403


def test_finance_officer_can_delete_unused_budget(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    finance = create_user(
        client,
        db_session,
        "budget.finance@example.com",
        UserRole.FINANCE_OFFICER,
    )

    response = client.delete(
        f"/budgets/{created.json()['id']}",
        headers=login(client, finance.email),
    )

    assert response.status_code == 204


def test_cannot_delete_budget_with_recorded_expenses(client, db_session):
    context = setup_budget_context(client, db_session)
    created = create_budget(client, context)

    expense = Expense(
        project_id=context["project_id"],
        category="food",
        amount=1000,
        description="Food supplies",
        expense_date=date(2026, 11, 10),
        created_by=context["user_id"],
    )
    db_session.add(expense)
    db_session.commit()

    finance = create_user(
        client,
        db_session,
        "budget.finance2@example.com",
        UserRole.FINANCE_OFFICER,
    )

    response = client.delete(
        f"/budgets/{created.json()['id']}",
        headers=login(client, finance.email),
    )

    assert response.status_code == 400
    assert "recorded expenses" in response.json()["detail"]
