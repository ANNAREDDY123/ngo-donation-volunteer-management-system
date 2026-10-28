
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus


def create_volunteer_user(client, db_session, email="volunteer@example.com"):
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Test Volunteer",
            "password": "SecurePass123!",
            "role": "volunteer",
        },
    )
    assert registration.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def create_manager_headers(client, db_session):
    email = "volunteer.manager@example.com"
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Volunteer Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert registration.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = UserRole.VOLUNTEER_COORDINATOR
    db_session.commit()

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "SecurePass123!",
        },
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_list_volunteers_requires_authentication(client):
    response = client.get("/volunteers")
    assert response.status_code == 401


def test_create_volunteer_profile(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    response = client.post(
        "/volunteers",
        headers=headers,
        json={
            "user_id": user.id,
            "phone": "9876543210",
            "address": "Hyderabad",
            "skills": "Teaching, fundraising",
            "availability": "Weekends",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user.id
    assert data["phone"] == "9876543210"
    assert data["status"] == "active"


def test_donor_cannot_create_volunteer_profile(client, access_token):
    response = client.post(
        "/volunteers",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "user_id": 1,
            "phone": "9876543210",
        },
    )
    assert response.status_code == 403


def test_create_profile_requires_volunteer_role(client, db_session):
    headers = create_manager_headers(client, db_session)

    registration = client.post(
        "/auth/register",
        json={
            "email": "not.volunteer@example.com",
            "full_name": "Ordinary Donor",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert registration.status_code == 201

    user = db_session.scalar(
        select(User).where(User.email == "not.volunteer@example.com")
    )
    assert user is not None

    response = client.post(
        "/volunteers",
        headers=headers,
        json={
            "user_id": user.id,
            "phone": "9876543210",
        },
    )
    assert response.status_code == 400


def test_create_duplicate_volunteer_profile(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    payload = {"user_id": user.id, "phone": "9876543210"}

    first = client.post("/volunteers", headers=headers, json=payload)
    assert first.status_code == 201

    second = client.post("/volunteers", headers=headers, json=payload)
    assert second.status_code == 400


def test_create_volunteer_rejects_invalid_phone(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    response = client.post(
        "/volunteers",
        headers=headers,
        json={
            "user_id": user.id,
            "phone": "123",
        },
    )
    assert response.status_code == 422


def test_list_volunteers(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    created = client.post(
        "/volunteers",
        headers=headers,
        json={
            "user_id": user.id,
            "phone": "9876543210",
            "skills": "Teaching",
        },
    )
    assert created.status_code == 201

    response = client.get("/volunteers", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_volunteer_by_id(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    created = client.post(
        "/volunteers",
        headers=headers,
        json={"user_id": user.id, "phone": "9876543210"},
    )
    assert created.status_code == 201

    volunteer_id = created.json()["id"]
    response = client.get(
        f"/volunteers/{volunteer_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == volunteer_id


def test_update_volunteer_status(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    created = client.post(
        "/volunteers",
        headers=headers,
        json={"user_id": user.id, "phone": "9876543210"},
    )
    assert created.status_code == 201

    volunteer_id = created.json()["id"]
    response = client.patch(
        f"/volunteers/{volunteer_id}",
        headers=headers,
        json={"status": "inactive"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_delete_volunteer_profile(client, db_session):
    headers = create_manager_headers(client, db_session)
    user = create_volunteer_user(client, db_session)

    created = client.post(
        "/volunteers",
        headers=headers,
        json={"user_id": user.id, "phone": "9876543210"},
    )
    assert created.status_code == 201

    volunteer_id = created.json()["id"]
    response = client.delete(
        f"/volunteers/{volunteer_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert db_session.get(Volunteer, volunteer_id) is None


def test_missing_volunteer_returns_404(client, db_session):
    headers = create_manager_headers(client, db_session)

    response = client.get("/volunteers/99999", headers=headers)
    assert response.status_code == 404
