
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


def setup_report_user(client, db_session, role=UserRole.NGO_MANAGER):
    user = create_user(
        client,
        db_session,
        f"reports.{role.value.lower()}@example.com",
        role,
    )
    return {"user": user, "headers": login(client, user.email)}


def test_donation_report_requires_authentication(client):
    response = client.get("/reports/donations.csv")
    assert response.status_code == 401


def test_donor_cannot_access_reports(client, db_session):
    context = setup_report_user(client, db_session, UserRole.DONOR)
    response = client.get(
        "/reports/donations.csv", headers=context["headers"]
    )
    assert response.status_code == 403


def test_manager_can_download_donation_report(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/donations.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment;" in response.headers["content-disposition"]
    assert "Donation ID" in response.text
    assert "Campaign" in response.text


def test_campaign_report_has_expected_headers(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/campaigns.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert "Campaign ID" in response.text
    assert "Goal Amount" in response.text
    assert "Start Date" in response.text


def test_expense_report_has_expected_headers(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/expenses.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert "Expense ID" in response.text
    assert "Project" in response.text
    assert "Expense Date" in response.text


def test_beneficiary_report_has_expected_headers(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/beneficiaries.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert "Beneficiary ID" in response.text
    assert "Full Name" in response.text
    assert "Support Needs" in response.text


def test_impact_report_has_expected_headers(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/impact.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert "Impact ID" in response.text
    assert "Progress Percentage" in response.text
    assert "Target" in response.text


def test_invalid_donation_date_range_is_rejected(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/donations.csv?date_from=2026-12-31&date_to=2026-01-01",
        headers=context["headers"],
    )

    assert response.status_code == 422
    assert "date_from must be on or before date_to" in response.json()["detail"]


def test_invalid_expense_date_range_is_rejected(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/expenses.csv?date_from=2026-12-31&date_to=2026-01-01",
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_invalid_campaign_id_is_rejected(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/donations.csv?campaign_id=0",
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_report_supports_valid_date_filters(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/donations.csv?date_from=2026-01-01&date_to=2026-12-31",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert "Donation Date" in response.text


def test_csv_download_uses_utf8_bom(client, db_session):
    context = setup_report_user(client, db_session)
    response = client.get(
        "/reports/campaigns.csv", headers=context["headers"]
    )

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
