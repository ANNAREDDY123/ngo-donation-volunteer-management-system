
from app.models.notification import Notification, NotificationType
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


def setup_users(client, db_session):
    manager = create_user(
        client,
        db_session,
        "notifications.manager@example.com",
        UserRole.NGO_MANAGER,
    )
    recipient = create_user(
        client,
        db_session,
        "notifications.recipient@example.com",
        UserRole.DONOR,
    )
    return {
        "manager": manager,
        "recipient": recipient,
        "manager_headers": login(client, manager.email),
        "recipient_headers": login(client, recipient.email),
    }


def payload(user_id, title="Welcome"):
    return {
        "user_id": user_id,
        "title": title,
        "message": "This is a test notification.",
        "notification_type": "general",
    }


def create_notification(client, users, title="Welcome"):
    return client.post(
        "/notifications",
        json=payload(users["recipient"].id, title),
        headers=users["manager_headers"],
    )


def test_create_notification(client, db_session):
    users = setup_users(client, db_session)
    response = create_notification(client, users)

    assert response.status_code == 201
    assert response.json()["user_id"] == users["recipient"].id
    assert response.json()["title"] == "Welcome"
    assert response.json()["is_read"] is False
    assert response.json()["read_at"] is None


def test_create_notification_requires_authentication(client, db_session):
    users = setup_users(client, db_session)

    response = client.post(
        "/notifications",
        json=payload(users["recipient"].id),
    )

    assert response.status_code == 401


def test_donor_cannot_create_notification(client, db_session):
    users = setup_users(client, db_session)

    response = client.post(
        "/notifications",
        json=payload(users["recipient"].id),
        headers=users["recipient_headers"],
    )

    assert response.status_code == 403


def test_create_notification_for_missing_user(client, db_session):
    users = setup_users(client, db_session)

    response = client.post(
        "/notifications",
        json=payload(999999),
        headers=users["manager_headers"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User not found"


def test_blank_title_is_rejected(client, db_session):
    users = setup_users(client, db_session)
    data = payload(users["recipient"].id, "   ")

    response = client.post(
        "/notifications",
        json=data,
        headers=users["manager_headers"],
    )

    assert response.status_code == 422


def test_blank_message_is_rejected(client, db_session):
    users = setup_users(client, db_session)
    data = payload(users["recipient"].id)
    data["message"] = "   "

    response = client.post(
        "/notifications",
        json=data,
        headers=users["manager_headers"],
    )

    assert response.status_code == 422


def test_user_lists_own_notifications_only(client, db_session):
    users = setup_users(client, db_session)
    create_notification(client, users, "Recipient notification")

    response = client.get(
        "/notifications",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Recipient notification"

    manager_response = client.get(
        "/notifications",
        headers=users["manager_headers"],
    )
    assert manager_response.status_code == 200
    assert manager_response.json()["total"] == 0


def test_get_own_notification(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    response = client.get(
        f"/notifications/{created.json()['id']}",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Welcome"


def test_user_cannot_get_another_users_notification(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    response = client.get(
        f"/notifications/{created.json()['id']}",
        headers=users["manager_headers"],
    )

    assert response.status_code == 404


def test_mark_notification_as_read(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    response = client.patch(
        f"/notifications/{created.json()['id']}/read",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert response.json()["read_at"] is not None


def test_marking_read_twice_is_safe(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)
    notification_id = created.json()["id"]

    first = client.patch(
        f"/notifications/{notification_id}/read",
        headers=users["recipient_headers"],
    )
    second = client.patch(
        f"/notifications/{notification_id}/read",
        headers=users["recipient_headers"],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["is_read"] is True


def test_unread_only_filter(client, db_session):
    users = setup_users(client, db_session)
    first = create_notification(client, users, "First")
    create_notification(client, users, "Second")

    client.patch(
        f"/notifications/{first.json()['id']}/read",
        headers=users["recipient_headers"],
    )

    response = client.get(
        "/notifications?unread_only=true",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Second"
    assert response.json()["unread_count"] == 1


def test_mark_all_notifications_read(client, db_session):
    users = setup_users(client, db_session)
    create_notification(client, users, "First")
    create_notification(client, users, "Second")

    response = client.patch(
        "/notifications/read-all",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    listing = client.get(
        "/notifications",
        headers=users["recipient_headers"],
    )
    assert listing.json()["unread_count"] == 0


def test_mark_all_read_when_none_are_unread(client, db_session):
    users = setup_users(client, db_session)

    response = client.patch(
        "/notifications/read-all",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 0


def test_delete_own_notification(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    response = client.delete(
        f"/notifications/{created.json()['id']}",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 204


def test_user_cannot_delete_another_users_notification(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    response = client.delete(
        f"/notifications/{created.json()['id']}",
        headers=users["manager_headers"],
    )

    assert response.status_code == 404


def test_missing_notification_returns_404(client, db_session):
    users = setup_users(client, db_session)

    response = client.get(
        "/notifications/999999",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 404


def test_filter_by_notification_type(client, db_session):
    users = setup_users(client, db_session)
    created = create_notification(client, users)

    notification = db_session.get(Notification, created.json()["id"])
    notification.notification_type = NotificationType.DONATION
    db_session.commit()

    response = client.get(
        "/notifications?notification_type=donation",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["notification_type"] == "donation"


def test_pagination_limit(client, db_session):
    users = setup_users(client, db_session)
    create_notification(client, users, "First")
    create_notification(client, users, "Second")
    create_notification(client, users, "Third")

    response = client.get(
        "/notifications?skip=1&limit=1",
        headers=users["recipient_headers"],
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["total"] == 3
    assert response.json()["skip"] == 1
    assert response.json()["limit"] == 1
