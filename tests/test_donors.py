
from sqlalchemy import select

from app.models.donor import Donor, DonorStatus
from app.models.user import User, UserRole


def manager_headers(client, db_session, email="manager@example.com"):
    """Create a manager test account and return its authorization header."""
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Test Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert response.status_code == 201

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

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def donor_payload(email="ravi@example.com"):
    return {
        "full_name": "Ravi Kumar",
        "email": email,
        "phone": "9876543210",
        "donor_type": "individual",
        "address": "Hyderabad",
    }


def test_list_donors_requires_authentication(client):
    response = client.get("/donors")
    assert response.status_code == 401


def test_donor_role_cannot_create_donor(client, access_token):
    response = client.post(
        "/donors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=donor_payload(),
    )
    assert response.status_code == 403


def test_create_donor_success(client, db_session):
    headers = manager_headers(client, db_session)

    response = client.post(
        "/donors",
        headers=headers,
        json=donor_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Ravi Kumar"
    assert data["email"] == "ravi@example.com"
    assert data["donor_type"] == "individual"
    assert data["status"] == "active"
    assert data["id"] > 0


def test_create_organization_without_name_returns_422(client, db_session):
    headers = manager_headers(client, db_session)

    payload = donor_payload("org@example.com")
    payload["donor_type"] = "organization"

    response = client.post(
        "/donors",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422


def test_create_donor_duplicate_email_returns_conflict(client, db_session):
    headers = manager_headers(client, db_session)

    first = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("duplicate@example.com"),
    )
    assert first.status_code == 201

    second = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("duplicate@example.com"),
    )
    assert second.status_code in (400, 409)


def test_list_donors_returns_created_donor(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("list@example.com"),
    )
    assert created.status_code == 201

    response = client.get("/donors", headers=headers)

    assert response.status_code == 200
    assert any(
        item["email"] == "list@example.com"
        for item in response.json()
    )


def test_get_donor_by_id(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("get@example.com"),
    )
    assert created.status_code == 201
    donor_id = created.json()["id"]

    response = client.get(
        f"/donors/{donor_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "get@example.com"


def test_get_nonexistent_donor_returns_404(client, db_session):
    headers = manager_headers(client, db_session)

    response = client.get("/donors/99999", headers=headers)

    assert response.status_code == 404


def test_update_donor(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("update@example.com"),
    )
    assert created.status_code == 201
    donor_id = created.json()["id"]

    response = client.patch(
        f"/donors/{donor_id}",
        headers=headers,
        json={"full_name": "Ravi Updated"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ravi Updated"


def test_delete_donor(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("delete@example.com"),
    )
    assert created.status_code == 201
    donor_id = created.json()["id"]

    response = client.delete(
        f"/donors/{donor_id}",
        headers=headers,
    )

    assert response.status_code == 204

    deleted = db_session.scalar(
        select(Donor).where(Donor.id == donor_id)
    )
    assert deleted is None


def test_update_donor_status(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/donors",
        headers=headers,
        json=donor_payload("status@example.com"),
    )
    assert created.status_code == 201
    donor_id = created.json()["id"]

    response = client.patch(
        f"/donors/{donor_id}",
        headers=headers,
        json={"status": "inactive"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == DonorStatus.INACTIVE.value
