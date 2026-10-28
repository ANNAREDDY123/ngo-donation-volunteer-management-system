
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


def setup_context(client, db_session):
    manager = create_user(
        client,
        db_session,
        "beneficiary.manager@example.com",
        UserRole.NGO_MANAGER,
    )
    return {
        "user_id": manager.id,
        "headers": login(client, manager.email),
    }


def beneficiary_payload(full_name="Test Beneficiary"):
    return {
        "full_name": full_name,
        "category": "low_income_families",
        "phone": "9876543210",
        "email": "beneficiary@example.com",
        "address": "Hyderabad",
        "household_size": 4,
        "support_needs": "Food and education support",
        "notes": "Registered through the community program",
    }


def create_beneficiary(client, context, full_name="Test Beneficiary"):
    return client.post(
        "/beneficiaries",
        json=beneficiary_payload(full_name),
        headers=context["headers"],
    )


def test_create_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    response = create_beneficiary(client, context)

    assert response.status_code == 201
    assert response.json()["full_name"] == "Test Beneficiary"
    assert response.json()["status"] == "active"
    assert response.json()["household_size"] == 4
    assert response.json()["created_by"] == context["user_id"]


def test_create_beneficiary_requires_authentication(client, db_session):
    response = client.post(
        "/beneficiaries",
        json=beneficiary_payload(),
    )
    assert response.status_code == 401


def test_donor_cannot_create_beneficiary(client, db_session):
    donor = create_user(
        client,
        db_session,
        "beneficiary.donor@example.com",
        UserRole.DONOR,
    )

    response = client.post(
        "/beneficiaries",
        json=beneficiary_payload(),
        headers=login(client, donor.email),
    )
    assert response.status_code == 403


def test_empty_beneficiary_name_is_rejected(client, db_session):
    context = setup_context(client, db_session)

    response = client.post(
        "/beneficiaries",
        json=beneficiary_payload("   "),
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_invalid_phone_is_rejected(client, db_session):
    context = setup_context(client, db_session)
    payload = beneficiary_payload()
    payload["phone"] = "123"

    response = client.post(
        "/beneficiaries",
        json=payload,
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_invalid_email_is_rejected(client, db_session):
    context = setup_context(client, db_session)
    payload = beneficiary_payload()
    payload["email"] = "not-an-email"

    response = client.post(
        "/beneficiaries",
        json=payload,
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_household_size_must_be_positive(client, db_session):
    context = setup_context(client, db_session)
    payload = beneficiary_payload()
    payload["household_size"] = 0

    response = client.post(
        "/beneficiaries",
        json=payload,
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_list_beneficiaries(client, db_session):
    context = setup_context(client, db_session)
    create_beneficiary(client, context, "Anita Rao")
    create_beneficiary(client, context, "Ravi Kumar")

    response = client.get(
        "/beneficiaries",
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_beneficiaries_by_name(client, db_session):
    context = setup_context(client, db_session)
    create_beneficiary(client, context, "Anita Rao")
    create_beneficiary(client, context, "Ravi Kumar")

    response = client.get(
        "/beneficiaries?search=Anita",
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["full_name"] == "Anita Rao"


def test_filter_beneficiaries_by_category(client, db_session):
    context = setup_context(client, db_session)
    create_beneficiary(client, context)

    payload = beneficiary_payload("Senior Citizen")
    payload["category"] = "elderly"
    client.post(
        "/beneficiaries",
        json=payload,
        headers=context["headers"],
    )

    response = client.get(
        "/beneficiaries?category=elderly",
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "elderly"


def test_filter_beneficiaries_by_status(client, db_session):
    context = setup_context(client, db_session)
    created = create_beneficiary(client, context)

    client.patch(
        f"/beneficiaries/{created.json()['id']}",
        json={"status": "inactive"},
        headers=context["headers"],
    )

    response = client.get(
        "/beneficiaries?status=inactive",
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "inactive"


def test_get_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    created = create_beneficiary(client, context)

    response = client.get(
        f"/beneficiaries/{created.json()['id']}",
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["email"] == "beneficiary@example.com"


def test_update_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    created = create_beneficiary(client, context)

    response = client.patch(
        f"/beneficiaries/{created.json()['id']}",
        json={"address": "New Hyderabad Address", "household_size": 5},
        headers=context["headers"],
    )
    assert response.status_code == 200
    assert response.json()["address"] == "New Hyderabad Address"
    assert response.json()["household_size"] == 5


def test_donor_cannot_view_beneficiaries(client, db_session):
    context = setup_context(client, db_session)
    create_beneficiary(client, context)

    donor = create_user(
        client,
        db_session,
        "beneficiary.viewer@example.com",
        UserRole.DONOR,
    )

    response = client.get(
        "/beneficiaries",
        headers=login(client, donor.email),
    )
    assert response.status_code == 403


def test_only_super_admin_can_delete_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    created = create_beneficiary(client, context)

    response = client.delete(
        f"/beneficiaries/{created.json()['id']}",
        headers=context["headers"],
    )
    assert response.status_code == 403


def test_super_admin_can_delete_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    created = create_beneficiary(client, context)

    admin = create_user(
        client,
        db_session,
        "beneficiary.admin@example.com",
        UserRole.SUPER_ADMIN,
    )

    response = client.delete(
        f"/beneficiaries/{created.json()['id']}",
        headers=login(client, admin.email),
    )
    assert response.status_code == 204


def test_missing_beneficiary_returns_404(client, db_session):
    context = setup_context(client, db_session)

    response = client.get(
        "/beneficiaries/999999",
        headers=context["headers"],
    )
    assert response.status_code == 404
