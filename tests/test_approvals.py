
from datetime import date

from app.models.project import Project, ProjectStatus
from app.models.project_approval import ApprovalStatus
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


def setup_approval_context(client, db_session):
    manager = create_user(
        client, db_session,
        "approval.manager@example.com",
        UserRole.NGO_MANAGER,
    )
    admin = create_user(
        client, db_session,
        "approval.admin@example.com",
        UserRole.SUPER_ADMIN,
    )

    project = Project(
        title="Community Education Project",
        description="Provide educational support to children.",
        location="Hyderabad",
        start_date=date(2026, 11, 1),
        end_date=date(2027, 3, 31),
        status=ProjectStatus.DRAFT,
        created_by=manager.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    return {
        "project_id": project.id,
        "manager_headers": login(client, manager.email),
        "admin_headers": login(client, admin.email),
        "manager_id": manager.id,
        "admin_id": admin.id,
    }


def submit(client, project_id, headers=None):
    return client.post(
        f"/approvals/projects/{project_id}/submit",
        json={"comments": "Ready for review"},
        headers=headers,
    )


def test_submit_project_for_approval(client, db_session):
    context = setup_approval_context(client, db_session)
    response = submit(
        client, context["project_id"], context["manager_headers"]
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["submitted_by"] == context["manager_id"]


def test_submit_approval_requires_authentication(client, db_session):
    context = setup_approval_context(client, db_session)
    response = submit(client, context["project_id"])
    assert response.status_code == 401


def test_submit_unknown_project_fails(client, db_session):
    context = setup_approval_context(client, db_session)
    response = submit(
        client, 999999, context["manager_headers"]
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Project not found"


def test_duplicate_pending_submission_is_rejected(client, db_session):
    context = setup_approval_context(client, db_session)
    first = submit(
        client, context["project_id"], context["manager_headers"]
    )
    second = submit(
        client, context["project_id"], context["manager_headers"]
    )
    assert first.status_code == 201
    assert second.status_code == 400
    assert "pending approval" in second.json()["detail"]


def test_admin_can_approve_project(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.post(
        f"/approvals/{submitted.json()['id']}/decision",
        json={"decision": "approved", "comments": "Approved for launch"},
        headers=context["admin_headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["reviewed_by"] == context["admin_id"]
    assert response.json()["review_comments"] == "Approved for launch"

    project = db_session.get(Project, context["project_id"])
    assert project.status == ProjectStatus.ACTIVE


def test_admin_can_reject_project(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.post(
        f"/approvals/{submitted.json()['id']}/decision",
        json={"decision": "rejected", "comments": "Revise the budget"},
        headers=context["admin_headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    project = db_session.get(Project, context["project_id"])
    assert project.status == ProjectStatus.DRAFT


def test_manager_cannot_decide_approval(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.post(
        f"/approvals/{submitted.json()['id']}/decision",
        json={"decision": "approved"},
        headers=context["manager_headers"],
    )
    assert response.status_code == 403


def test_cannot_review_own_submission(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    from app.services.approvals import decide_project_approval

    manager = db_session.get(User, context["manager_id"])

    try:
        decide_project_approval(
            db_session,
            submitted.json()["id"],
            manager,
            ApprovalStatus.APPROVED,
            "Self approval",
        )
        assert False, "Expected self-approval to be rejected"
    except ValueError as exc:
        assert "cannot approve or reject their own submission" in str(exc)


def test_cannot_decide_same_approval_twice(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )
    approval_id = submitted.json()["id"]

    first = client.post(
        f"/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers=context["admin_headers"],
    )
    second = client.post(
        f"/approvals/{approval_id}/decision",
        json={"decision": "rejected"},
        headers=context["admin_headers"],
    )
    assert first.status_code == 200
    assert second.status_code == 400


def test_get_project_approval_history(client, db_session):
    context = setup_approval_context(client, db_session)
    submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.get(
        f"/approvals/projects/{context['project_id']}",
        headers=context["manager_headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "pending"


def test_approval_decision_requires_super_admin(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.post(
        f"/approvals/{submitted.json()['id']}/decision",
        json={"decision": "approved"},
    )
    assert response.status_code == 401


def test_invalid_decision_is_rejected(client, db_session):
    context = setup_approval_context(client, db_session)
    submitted = submit(
        client, context["project_id"], context["manager_headers"]
    )

    response = client.post(
        f"/approvals/{submitted.json()['id']}/decision",
        json={"decision": "pending"},
        headers=context["admin_headers"],
    )
    assert response.status_code == 422


def test_rejected_project_can_be_resubmitted(client, db_session):
    context = setup_approval_context(client, db_session)
    first = submit(
        client, context["project_id"], context["manager_headers"]
    )

    rejected = client.post(
        f"/approvals/{first.json()['id']}/decision",
        json={"decision": "rejected", "comments": "Revise the plan"},
        headers=context["admin_headers"],
    )
    assert rejected.status_code == 200

    second = submit(
        client, context["project_id"], context["manager_headers"]
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["status"] == "pending"
