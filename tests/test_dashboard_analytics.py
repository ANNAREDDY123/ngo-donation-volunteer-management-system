
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


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard/overview")
    assert response.status_code == 401


def test_donor_cannot_access_dashboard(client, db_session):
    donor = create_user(
        client,
        db_session,
        "dashboard.donor@example.com",
        UserRole.DONOR,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, donor.email),
    )

    assert response.status_code == 403


def test_super_admin_can_access_dashboard(client, db_session):
    admin = create_user(
        client,
        db_session,
        "dashboard.admin@example.com",
        UserRole.SUPER_ADMIN,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, admin.email),
    )

    assert response.status_code == 200


def test_manager_can_access_dashboard(client, db_session):
    manager = create_user(
        client,
        db_session,
        "dashboard.manager@example.com",
        UserRole.NGO_MANAGER,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, manager.email),
    )

    assert response.status_code == 200


def test_finance_officer_can_access_dashboard(client, db_session):
    finance = create_user(
        client,
        db_session,
        "dashboard.finance@example.com",
        UserRole.FINANCE_OFFICER,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, finance.email),
    )

    assert response.status_code == 200


def test_volunteer_coordinator_can_access_dashboard(client, db_session):
    coordinator = create_user(
        client,
        db_session,
        "dashboard.coordinator@example.com",
        UserRole.VOLUNTEER_COORDINATOR,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, coordinator.email),
    )

    assert response.status_code == 200


def test_dashboard_returns_all_sections(client, db_session):
    manager = create_user(
        client,
        db_session,
        "dashboard.sections@example.com",
        UserRole.NGO_MANAGER,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, manager.email),
    )

    assert response.status_code == 200
    data = response.json()

    expected_sections = {
        "donations",
        "campaigns",
        "donors",
        "volunteers",
        "projects",
        "finance",
        "beneficiaries",
        "impact",
        "inventory",
    }
    assert set(data.keys()) == expected_sections


def test_empty_dashboard_returns_zero_counts(client, db_session):
    manager = create_user(
        client,
        db_session,
        "dashboard.empty@example.com",
        UserRole.NGO_MANAGER,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, manager.email),
    )

    assert response.status_code == 200
    data = response.json()

    assert data["donations"]["total_count"] == 0
    assert data["donations"]["completed_amount"] == 0
    assert data["campaigns"]["total_count"] == 0
    assert data["donors"]["total_count"] == 0
    assert data["volunteers"]["total_count"] == 0
    assert data["projects"]["total_count"] == 0
    assert data["finance"]["total_expenses"] == 0
    assert data["finance"]["total_budget_allocated"] == 0
    assert data["beneficiaries"]["total_count"] == 0
    assert data["impact"]["total_count"] == 0
    assert data["impact"]["overall_progress_percentage"] == 0
    assert data["inventory"]["item_count"] == 0
    assert data["inventory"]["total_quantity"] == 0


def test_dashboard_progress_is_zero_when_there_are_no_targets(
    client,
    db_session,
):
    manager = create_user(
        client,
        db_session,
        "dashboard.progress@example.com",
        UserRole.NGO_MANAGER,
    )

    response = client.get(
        "/dashboard/overview",
        headers=login(client, manager.email),
    )

    assert response.status_code == 200
    assert response.json()["impact"]["overall_progress_percentage"] == 0.0
