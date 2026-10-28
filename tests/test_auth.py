def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_donor(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "newdonor@example.com",
            "full_name": "New Donor",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "newdonor@example.com"
    assert response.json()["role"] == "donor"
    assert "hashed_password" not in response.json()


def test_register_volunteer(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "volunteer@example.com",
            "full_name": "Test Volunteer",
            "password": "VolunteerPass123!",
            "role": "volunteer",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "volunteer"


def test_duplicate_email_rejected(client, registered_user):
    response = client.post(
        "/auth/register",
        json={
            "email": "donor@example.com",
            "full_name": "Duplicate Donor",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )

    assert response.status_code == 409


def test_privileged_role_registration_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Fake Admin",
            "password": "SecurePass123!",
            "role": "super_admin",
        },
    )

    assert response.status_code == 422


def test_short_password_rejected(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "short@example.com",
            "full_name": "Short Password",
            "password": "123",
            "role": "donor",
        },
    )

    assert response.status_code == 422


def test_login_success(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_current_user(client, registered_user, access_token):
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "donor@example.com"


def test_current_user_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_refresh_token(client, registered_user):
    login = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


def test_access_token_rejected_as_refresh_token(
    client, registered_user
):
    login = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["access_token"]},
    )

    assert response.status_code == 401


def test_password_reset_request(client, registered_user):
    response = client.post(
        "/auth/password-reset/request",
        json={"email": "donor@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json().get("reset_token")


def test_password_reset_confirm(client, registered_user):
    request = client.post(
        "/auth/password-reset/request",
        json={"email": "donor@example.com"},
    )

    token = request.json()["reset_token"]

    reset = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "NewSecurePass123!",
        },
    )

    assert reset.status_code == 200

    login = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "NewSecurePass123!",
        },
    )

    assert login.status_code == 200


def test_password_reset_token_cannot_be_reused(
    client, registered_user
):
    request = client.post(
        "/auth/password-reset/request",
        json={"email": "donor@example.com"},
    )

    token = request.json()["reset_token"]
    payload = {
        "token": token,
        "new_password": "NewSecurePass123!",
    }

    first = client.post(
        "/auth/password-reset/confirm",
        json=payload,
    )
    second = client.post(
        "/auth/password-reset/confirm",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_admin_endpoint_forbidden_for_donor(client, access_token):
    response = client.get(
        "/auth/admin-check",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403


def test_password_reset_unknown_email_is_generic(client):
    response = client.post(
        "/auth/password-reset/request",
        json={"email": "unknown@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json().get("reset_token") is None