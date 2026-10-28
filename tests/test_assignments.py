
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.assignment import Assignment, AssignmentStatus
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus


def create_manager_and_volunteer(client, db_session):
    manager_email = "assignment.manager@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": manager_email,
            "full_name": "Assignment Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert response.status_code == 201

    manager = db_session.scalar(
        select(User).where(User.email == manager_email)
    )
    assert manager is not None
    manager.role = UserRole.VOLUNTEER_COORDINATOR
    db_session.commit()

    login = client.post(
        "/auth/login",
        json={
            "email": manager_email,
            "password": "SecurePass123!",
        },
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    volunteer_email = "assigned.volunteer@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": volunteer_email,
            "full_name": "Assigned Volunteer",
            "password": "SecurePass123!",
            "role": "volunteer",
        },
    )
    assert response.status_code == 201

    volunteer_user = db_session.scalar(
        select(User).where(User.email == volunteer_email)
    )
    assert volunteer_user is not None

    volunteer = Volunteer(
        user_id=volunteer_user.id,
        phone="9876543210",
        status=VolunteerStatus.ACTIVE,
    )
    db_session.add(volunteer)
    db_session.commit()
    db_session.refresh(volunteer)

    return headers, manager, volunteer, volunteer_user


def assignment_payload(volunteer_id):
    return {
        "volunteer_id": volunteer_id,
        "title": "Community Food Distribution",
        "description": "Help organize and distribute food packages.",
        "priority": "high",
        "due_date": (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).isoformat(),
    }


def test_list_assignments_requires_authentication(client):
    response = client.get("/assignments")
    assert response.status_code == 401


def test_create_assignment_success(client, db_session):
    headers, manager, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    response = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["volunteer_id"] == volunteer.id
    assert data["status"] == "assigned"
    assert data["priority"] == "high"
    assert data["created_by"] == manager.id


def test_donor_cannot_create_assignment(client, access_token):
    response = client.post(
        "/assignments",
        headers={"Authorization": f"Bearer {access_token}"},
        json=assignment_payload(1),
    )
    assert response.status_code == 403


def test_create_assignment_rejects_missing_volunteer(client, db_session):
    headers, _, _, _ = create_manager_and_volunteer(client, db_session)

    response = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(99999),
    )
    assert response.status_code == 400


def test_create_assignment_rejects_inactive_volunteer(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )
    volunteer.status = VolunteerStatus.INACTIVE
    db_session.commit()

    response = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert response.status_code == 400


def test_list_assignments(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    response = client.get(
        "/assignments",
        headers=headers,
        params={"volunteer_id": volunteer.id, "status": "assigned"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_assignment_by_id(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    assignment_id = created.json()["id"]
    response = client.get(
        f"/assignments/{assignment_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == assignment_id


def test_update_assignment_status(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    response = client.patch(
        f"/assignments/{created.json()['id']}",
        headers=headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_completed_assignment_cannot_be_reopened(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    assignment_id = created.json()["id"]
    assignment = db_session.get(Assignment, assignment_id)
    assert assignment is not None
    assignment.status = AssignmentStatus.COMPLETED
    db_session.commit()

    response = client.patch(
        f"/assignments/{assignment_id}",
        headers=headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 400


def test_delete_assigned_assignment(client, db_session):
    headers, _, volunteer, _ = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    assignment_id = created.json()["id"]
    response = client.delete(
        f"/assignments/{assignment_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert db_session.get(Assignment, assignment_id) is None


def test_volunteer_can_view_own_assignment(client, db_session):
    headers, _, volunteer, volunteer_user = create_manager_and_volunteer(
        client, db_session
    )

    created = client.post(
        "/assignments",
        headers=headers,
        json=assignment_payload(volunteer.id),
    )
    assert created.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": volunteer_user.email,
            "password": "SecurePass123!",
        },
    )
    assert login.status_code == 200
    volunteer_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    response = client.get(
        f"/assignments/{created.json()['id']}",
        headers=volunteer_headers,
    )
    assert response.status_code == 200


def test_missing_assignment_returns_404(client, db_session):
    headers, _, _, _ = create_manager_and_volunteer(client, db_session)

    response = client.get("/assignments/99999", headers=headers)
    assert response.status_code == 404
