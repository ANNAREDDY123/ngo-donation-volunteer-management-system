
from datetime import date

from app.models.beneficiary import Beneficiary, BeneficiaryCategory
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


def setup_context(client, db_session):
    manager = create_user(
        client,
        db_session,
        "impact.manager@example.com",
        UserRole.NGO_MANAGER,
    )

    project = Project(
        title="Community Education Project",
        description="Improve access to education.",
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


def impact_payload(project_id, metric_name="Meals Distributed"):
    return {
        "project_id": project_id,
        "metric_name": metric_name,
        "description": "Track the number of meals provided.",
        "unit": "meals",
        "target_value": 100,
        "actual_value": 0,
    }


def create_impact(client, context, metric_name="Meals Distributed"):
    return client.post(
        "/impacts",
        json=impact_payload(context["project_id"], metric_name),
        headers=context["headers"],
    )


def test_create_impact(client, db_session):
    context = setup_context(client, db_session)
    response = create_impact(client, context)

    assert response.status_code == 201
    assert response.json()["metric_name"] == "Meals Distributed"
    assert response.json()["target_value"] == 100
    assert response.json()["actual_value"] == 0
    assert response.json()["progress_percentage"] == 0
    assert response.json()["status"] == "in_progress"
    assert response.json()["recorded_by"] == context["user_id"]


def test_create_impact_requires_authentication(client, db_session):
    context = setup_context(client, db_session)

    response = client.post(
        "/impacts",
        json=impact_payload(context["project_id"]),
    )

    assert response.status_code == 401


def test_donor_cannot_create_impact(client, db_session):
    context = setup_context(client, db_session)
    donor = create_user(
        client,
        db_session,
        "impact.donor@example.com",
        UserRole.DONOR,
    )

    response = client.post(
        "/impacts",
        json=impact_payload(context["project_id"]),
        headers=login(client, donor.email),
    )

    assert response.status_code == 403


def test_impact_requires_existing_project(client, db_session):
    context = setup_context(client, db_session)

    response = client.post(
        "/impacts",
        json=impact_payload(999999),
        headers=context["headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Project not found"


def test_target_must_be_positive(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["target_value"] = 0

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_actual_value_cannot_be_negative(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["actual_value"] = -1

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_empty_metric_name_is_rejected(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"], "   ")

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 422


def test_progress_percentage_is_calculated(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["actual_value"] = 75

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 201
    assert response.json()["progress_percentage"] == 75.0
    assert response.json()["status"] == "in_progress"


def test_target_achievement_sets_achieved_status(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["actual_value"] = 100

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 201
    assert response.json()["progress_percentage"] == 100.0
    assert response.json()["status"] == "achieved"


def test_actual_value_can_exceed_target(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["actual_value"] = 125

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 201
    assert response.json()["progress_percentage"] == 125.0
    assert response.json()["status"] == "achieved"


def test_list_and_search_impacts(client, db_session):
    context = setup_context(client, db_session)
    create_impact(client, context, "Meals Distributed")
    create_impact(client, context, "Children Educated")

    response = client.get(
        "/impacts?metric_name=Children",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["metric_name"] == "Children Educated"


def test_filter_impacts_by_project(client, db_session):
    context = setup_context(client, db_session)
    create_impact(client, context)

    response = client.get(
        f"/impacts?project_id={context['project_id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_impact(client, db_session):
    context = setup_context(client, db_session)
    created = create_impact(client, context)

    response = client.get(
        f"/impacts/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["metric_name"] == "Meals Distributed"


def test_update_impact_recalculates_progress(client, db_session):
    context = setup_context(client, db_session)
    created = create_impact(client, context)

    response = client.patch(
        f"/impacts/{created.json()['id']}",
        json={"actual_value": 50},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["actual_value"] == 50
    assert response.json()["progress_percentage"] == 50.0
    assert response.json()["status"] == "in_progress"


def test_update_target_can_mark_impact_achieved(client, db_session):
    context = setup_context(client, db_session)
    created = create_impact(client, context)

    response = client.patch(
        f"/impacts/{created.json()['id']}",
        json={"actual_value": 100},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "achieved"


def test_missing_impact_returns_404(client, db_session):
    context = setup_context(client, db_session)

    response = client.get(
        "/impacts/999999",
        headers=context["headers"],
    )

    assert response.status_code == 404


def test_only_super_admin_can_delete_impact(client, db_session):
    context = setup_context(client, db_session)
    created = create_impact(client, context)

    response = client.delete(
        f"/impacts/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 403


def test_super_admin_can_delete_impact(client, db_session):
    context = setup_context(client, db_session)
    created = create_impact(client, context)

    admin = create_user(
        client,
        db_session,
        "impact.admin@example.com",
        UserRole.SUPER_ADMIN,
    )

    response = client.delete(
        f"/impacts/{created.json()['id']}",
        headers=login(client, admin.email),
    )

    assert response.status_code == 204


def test_impact_can_reference_existing_beneficiary(client, db_session):
    context = setup_context(client, db_session)

    beneficiary = Beneficiary(
        full_name="Community Beneficiary",
        category=BeneficiaryCategory.LOW_INCOME_FAMILIES,
        created_by=context["user_id"],
    )
    db_session.add(beneficiary)
    db_session.commit()
    db_session.refresh(beneficiary)

    payload = impact_payload(context["project_id"])
    payload["beneficiary_id"] = beneficiary.id

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 201
    assert response.json()["beneficiary_id"] == beneficiary.id


def test_impact_rejects_unknown_beneficiary(client, db_session):
    context = setup_context(client, db_session)
    payload = impact_payload(context["project_id"])
    payload["beneficiary_id"] = 999999

    response = client.post(
        "/impacts",
        json=payload,
        headers=context["headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Beneficiary not found"
