
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.campaign import Campaign, CampaignStatus
from app.models.user import User, UserRole


def manager_headers(client, db_session, email="campaign.manager@example.com"):
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Campaign Manager",
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


def campaign_payload(title="Education for Every Child"):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(days=30)

    return {
        "title": title,
        "description": "Fund educational resources for children in need.",
        "goal_amount": 50000,
        "currency": "INR",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def test_list_campaigns_requires_authentication(client):
    response = client.get("/campaigns")
    assert response.status_code == 401


def test_create_campaign_success(client, db_session):
    headers = manager_headers(client, db_session)

    response = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Education for Every Child"
    assert data["goal_amount"] == 50000
    assert data["currency"] == "INR"
    assert data["status"] == "draft"
    assert data["created_by"] > 0


def test_donor_cannot_create_campaign(client, access_token):
    response = client.post(
        "/campaigns",
        headers={"Authorization": f"Bearer {access_token}"},
        json=campaign_payload(),
    )
    assert response.status_code == 403


def test_create_campaign_rejects_nonpositive_goal(client, db_session):
    headers = manager_headers(client, db_session)

    payload = campaign_payload()
    payload["goal_amount"] = 0

    response = client.post("/campaigns", headers=headers, json=payload)
    assert response.status_code == 422


def test_create_campaign_rejects_end_date_before_start_date(
    client, db_session
):
    headers = manager_headers(client, db_session)

    payload = campaign_payload()
    payload["start_date"] = "2027-12-31T00:00:00+00:00"
    payload["end_date"] = "2027-01-01T00:00:00+00:00"

    response = client.post("/campaigns", headers=headers, json=payload)
    assert response.status_code == 422


def test_list_campaigns_returns_created_campaign(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload("Clean Water Project"),
    )
    assert created.status_code == 201

    response = client.get(
        "/campaigns",
        headers=headers,
        params={"search": "Clean Water"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Clean Water Project"


def test_get_campaign_by_id(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    response = client.get(
        f"/campaigns/{campaign_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == campaign_id


def test_get_missing_campaign_returns_404(client, db_session):
    headers = manager_headers(client, db_session)

    response = client.get("/campaigns/99999", headers=headers)
    assert response.status_code == 404


def test_update_campaign_title(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    response = client.patch(
        f"/campaigns/{campaign_id}",
        headers=headers,
        json={"title": "Updated Education Campaign"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Education Campaign"


def test_delete_draft_campaign(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    response = client.delete(
        f"/campaigns/{campaign_id}",
        headers=headers,
    )
    assert response.status_code == 204

    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is None


def test_active_campaign_cannot_be_deleted(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is not None
    campaign.status = CampaignStatus.ACTIVE
    db_session.commit()

    response = client.delete(
        f"/campaigns/{campaign_id}",
        headers=headers,
    )

    assert response.status_code == 400
    assert db_session.get(Campaign, campaign_id) is not None


def test_completed_campaign_cannot_be_reopened(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201

    campaign_id = created.json()["id"]
    campaign = db_session.get(Campaign, campaign_id)
    campaign.status = CampaignStatus.COMPLETED
    db_session.commit()

    response = client.patch(
        f"/campaigns/{campaign_id}",
        headers=headers,
        json={"status": "active"},
    )

    assert response.status_code == 400
    db_session.refresh(campaign)
    assert campaign.status == CampaignStatus.COMPLETED


def test_campaign_partial_date_update_preserves_date_range(
    client, db_session
):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201

    campaign_id = created.json()["id"]
    campaign = db_session.get(Campaign, campaign_id)

    response = client.patch(
        f"/campaigns/{campaign_id}",
        headers=headers,
        json={
            "start_date": (
                campaign.end_date + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 400



def test_cancelled_campaign_cannot_be_reopened(client, db_session):
    headers = manager_headers(client, db_session)

    created = client.post(
        "/campaigns",
        headers=headers,
        json=campaign_payload(),
    )
    assert created.status_code == 201

    campaign_id = created.json()["id"]
    campaign = db_session.get(Campaign, campaign_id)
    campaign.status = CampaignStatus.CANCELLED
    db_session.commit()

    response = client.patch(
        f"/campaigns/{campaign_id}",
        headers=headers,
        json={"status": "active"},
    )

    assert response.status_code == 400
    db_session.refresh(campaign)
    assert campaign.status == CampaignStatus.CANCELLED

