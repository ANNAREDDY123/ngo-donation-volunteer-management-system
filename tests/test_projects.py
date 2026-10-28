
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.project import Project, ProjectStatus
from app.models.user import User, UserRole


def manager_headers(client, db_session, email="project.manager@example.com"):
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Project Manager",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )
    assert registration.status_code == 201

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
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def project_payload(title="Community Education Program"):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(days=60)
    return {
        "title": title,
        "description": "Provide educational support to local children.",
        "location": "Hyderabad",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def test_list_projects_requires_authentication(client):
    response = client.get("/projects")
    assert response.status_code == 401


def test_create_project_success(client, db_session):
    headers = manager_headers(client, db_session)
    response = client.post(
        "/projects", headers=headers, json=project_payload()
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Community Education Program"
    assert data["status"] == "draft"
    assert data["created_by"] > 0


def test_donor_cannot_create_project(client, access_token):
    response = client.post(
        "/projects",
        headers={"Authorization": f"Bearer {access_token}"},
        json=project_payload(),
    )
    assert response.status_code == 403


def test_create_project_rejects_invalid_dates(client, db_session):
    headers = manager_headers(client, db_session)
    payload = project_payload()
    payload["start_date"] = "2027-12-31T00:00:00+00:00"
    payload["end_date"] = "2027-01-01T00:00:00+00:00"

    response = client.post("/projects", headers=headers, json=payload)
    assert response.status_code == 422


def test_list_and_search_projects(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects",
        headers=headers,
        json=project_payload("Community Health Program"),
    )
    assert created.status_code == 201

    response = client.get(
        "/projects",
        headers=headers,
        params={"search": "Health"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Community Health Program"


def test_get_project_by_id(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    project_id = created.json()["id"]
    response = client.get(f"/projects/{project_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_missing_project_returns_404(client, db_session):
    headers = manager_headers(client, db_session)
    response = client.get("/projects/99999", headers=headers)
    assert response.status_code == 404


def test_update_project_title(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    response = client.patch(
        f"/projects/{created.json()['id']}",
        headers=headers,
        json={"title": "Updated Community Project"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Community Project"


def test_project_status_transition(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    response = client.patch(
        f"/projects/{created.json()['id']}",
        headers=headers,
        json={"status": "active"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_completed_project_cannot_be_reopened(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    project_id = created.json()["id"]
    project = db_session.get(Project, project_id)
    assert project is not None
    project.status = ProjectStatus.COMPLETED
    db_session.commit()

    response = client.patch(
        f"/projects/{project_id}",
        headers=headers,
        json={"status": "active"},
    )

    assert response.status_code == 400


def test_delete_draft_project(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    project_id = created.json()["id"]
    response = client.delete(f"/projects/{project_id}", headers=headers)

    assert response.status_code == 204
    assert db_session.get(Project, project_id) is None


def test_active_project_cannot_be_deleted(client, db_session):
    headers = manager_headers(client, db_session)
    created = client.post(
        "/projects", headers=headers, json=project_payload()
    )
    assert created.status_code == 201

    project_id = created.json()["id"]
    project = db_session.get(Project, project_id)
    assert project is not None
    project.status = ProjectStatus.ACTIVE
    db_session.commit()

    response = client.delete(f"/projects/{project_id}", headers=headers)

    assert response.status_code == 400
    assert db_session.get(Project, project_id) is not None


def test_project_partial_date_update_preserves_date_range(
    client, db_session
):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/projects",
        headers=headers,
        json=project_payload(),
    )
    assert created.status_code == 201

    project_id = created.json()["id"]
    project = db_session.get(Project, project_id)

    response = client.patch(
        f"/projects/{project_id}",
        headers=headers,
        json={
            "start_date": (
                project.end_date + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 400

