
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.project import Project, ProjectStatus
from app.models.task import Milestone, ProjectTask, TaskStatus
from app.models.user import User, UserRole


def setup_project(client, db_session):
    email = "tasks.manager@example.com"
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Tasks Manager",
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
        json={"email": email, "password": "SecurePass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    start = datetime.now(timezone.utc) + timedelta(days=1)
    project = Project(
        title="Task Test Project",
        description="A project used for testing milestones and tasks.",
        location="Hyderabad",
        start_date=start,
        end_date=start + timedelta(days=60),
        status=ProjectStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return headers, user, project


def test_list_tasks_requires_authentication(client):
    response = client.get("/tasks")
    assert response.status_code == 401


def test_create_milestone(client, db_session):
    headers, user, project = setup_project(client, db_session)
    response = client.post(
        "/milestones",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Phase One",
            "description": "Complete the initial planning phase.",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["created_by"] == user.id


def test_create_milestone_rejects_missing_project(client, db_session):
    headers, _, _ = setup_project(client, db_session)
    response = client.post(
        "/milestones",
        headers=headers,
        json={
            "project_id": 99999,
            "title": "Phase One",
            "description": "Complete the initial planning phase.",
        },
    )
    assert response.status_code == 400


def test_list_milestones(client, db_session):
    headers, _, project = setup_project(client, db_session)
    created = client.post(
        "/milestones",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Phase One",
            "description": "Complete the initial planning phase.",
        },
    )
    assert created.status_code == 201

    response = client.get(
        "/milestones",
        headers=headers,
        params={"project_id": project.id},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_task(client, db_session):
    headers, user, project = setup_project(client, db_session)
    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Prepare materials",
            "description": "Prepare the required community project materials.",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "todo"
    assert response.json()["created_by"] == user.id


def test_create_task_with_milestone(client, db_session):
    headers, _, project = setup_project(client, db_session)
    milestone_response = client.post(
        "/milestones",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Phase One",
            "description": "Complete the initial planning phase.",
        },
    )
    assert milestone_response.status_code == 201

    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "project_id": project.id,
            "milestone_id": milestone_response.json()["id"],
            "title": "Prepare materials",
            "description": "Prepare the required community project materials.",
        },
    )
    assert response.status_code == 201
    assert response.json()["milestone_id"] == milestone_response.json()["id"]


def test_task_rejects_milestone_from_another_project(client, db_session):
    headers, _, project1 = setup_project(client, db_session)

    project2 = Project(
        title="Another Project",
        description="A second project used for validation tests.",
        start_date=datetime.now(timezone.utc),
        status=ProjectStatus.ACTIVE,
        created_by=project1.created_by,
    )
    db_session.add(project2)
    db_session.commit()
    db_session.refresh(project2)

    milestone = Milestone(
        project_id=project2.id,
        title="Other Phase",
        description="A milestone in another project.",
        created_by=project1.created_by,
    )
    db_session.add(milestone)
    db_session.commit()
    db_session.refresh(milestone)

    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "project_id": project1.id,
            "milestone_id": milestone.id,
            "title": "Prepare materials",
            "description": "Prepare the required community project materials.",
        },
    )
    assert response.status_code == 400


def test_list_tasks(client, db_session):
    headers, _, project = setup_project(client, db_session)
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Prepare materials",
            "description": "Prepare the required community project materials.",
        },
    )
    assert created.status_code == 201

    response = client.get(
        "/tasks",
        headers=headers,
        params={"project_id": project.id, "status": "todo"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_task_status(client, db_session):
    headers, _, project = setup_project(client, db_session)
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "project_id": project.id,
            "title": "Prepare materials",
            "description": "Prepare the required community project materials.",
        },
    )
    assert created.status_code == 201

    response = client.patch(
        f"/tasks/{created.json()['id']}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_missing_task_returns_404(client, db_session):
    headers, _, _ = setup_project(client, db_session)
    response = client.get("/tasks/99999", headers=headers)
    assert response.status_code == 404


def test_donor_cannot_create_milestone(client, access_token):
    response = client.post(
        "/milestones",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "project_id": 1,
            "title": "Phase One",
            "description": "Complete the initial planning phase.",
        },
    )
    assert response.status_code == 403
