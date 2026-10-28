
from app.models.inventory import InventoryItem, InventoryCategory
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


def setup_inventory_context(client, db_session):
    manager = create_user(
        client,
        db_session,
        "inventory.manager@example.com",
        UserRole.NGO_MANAGER,
    )
    return {
        "user_id": manager.id,
        "headers": login(client, manager.email),
    }


def item_payload(name="Rice Bags"):
    return {
        "name": name,
        "category": "food",
        "unit": "bag",
        "storage_location": "Main Store",
        "description": "Rice stock for beneficiaries",
    }


def create_item(client, context, name="Rice Bags"):
    return client.post(
        "/inventory/items",
        json=item_payload(name),
        headers=context["headers"],
    )


def receive(client, context, item_id, quantity=10):
    return client.post(
        f"/inventory/items/{item_id}/receive",
        json={"quantity": quantity, "reference": "GRN-001"},
        headers=context["headers"],
    )


def issue(client, context, item_id, quantity=3):
    return client.post(
        f"/inventory/items/{item_id}/issue",
        json={"quantity": quantity, "reference": "ISS-001"},
        headers=context["headers"],
    )


def test_create_inventory_item(client, db_session):
    context = setup_inventory_context(client, db_session)
    response = create_item(client, context)

    assert response.status_code == 201
    assert response.json()["name"] == "Rice Bags"
    assert response.json()["quantity"] == 0
    assert response.json()["created_by"] == context["user_id"]


def test_create_inventory_item_requires_authentication(client, db_session):
    response = client.post(
        "/inventory/items",
        json=item_payload(),
    )
    assert response.status_code == 401


def test_donor_cannot_create_inventory_item(client, db_session):
    create_user(
        client,
        db_session,
        "inventory.donor@example.com",
        UserRole.DONOR,
    )
    headers = login(client, "inventory.donor@example.com")

    response = client.post(
        "/inventory/items",
        json=item_payload(),
        headers=headers,
    )
    assert response.status_code == 403


def test_inventory_item_name_cannot_be_empty(client, db_session):
    context = setup_inventory_context(client, db_session)
    response = client.post(
        "/inventory/items",
        json={**item_payload(), "name": "   "},
        headers=context["headers"],
    )
    assert response.status_code == 422


def test_list_and_search_inventory_items(client, db_session):
    context = setup_inventory_context(client, db_session)
    create_item(client, context, "Rice Bags")
    create_item(client, context, "Medical Kits")

    response = client.get(
        "/inventory/items?search=Rice",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Rice Bags"


def test_filter_inventory_by_category(client, db_session):
    context = setup_inventory_context(client, db_session)
    create_item(client, context, "Rice Bags")
    client.post(
        "/inventory/items",
        json={
            "name": "First Aid Kits",
            "category": "medical",
            "unit": "kit",
        },
        headers=context["headers"],
    )

    response = client.get(
        "/inventory/items?category=medical",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "medical"


def test_get_inventory_item(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)

    response = client.get(
        f"/inventory/items/{created.json()['id']}",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Rice Bags"


def test_update_inventory_item_details(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)

    response = client.patch(
        f"/inventory/items/{created.json()['id']}",
        json={"storage_location": "Warehouse B"},
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert response.json()["storage_location"] == "Warehouse B"


def test_receive_stock_increases_quantity(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)

    response = receive(client, context, created.json()["id"], 10)

    assert response.status_code == 201
    assert response.json()["movement_type"] == "received"
    assert response.json()["quantity_after"] == 10

    item = client.get(
        f"/inventory/items/{created.json()['id']}",
        headers=context["headers"],
    )
    assert item.json()["quantity"] == 10


def test_issue_stock_decreases_quantity(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)
    item_id = created.json()["id"]
    receive(client, context, item_id, 10)

    response = issue(client, context, item_id, 3)

    assert response.status_code == 201
    assert response.json()["movement_type"] == "issued"
    assert response.json()["quantity_after"] == 7


def test_cannot_issue_more_than_available_stock(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)
    item_id = created.json()["id"]
    receive(client, context, item_id, 2)

    response = issue(client, context, item_id, 5)

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_stock_movement_quantity_must_be_positive(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)

    response = receive(client, context, created.json()["id"], 0)

    assert response.status_code == 422


def test_inventory_movement_history(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)
    item_id = created.json()["id"]
    receive(client, context, item_id, 10)
    issue(client, context, item_id, 2)

    response = client.get(
        f"/inventory/items/{item_id}/movements",
        headers=context["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {row["movement_type"] for row in response.json()} == {
        "received",
        "issued",
    }


def test_cannot_delete_item_with_stock_or_history(client, db_session):
    context = setup_inventory_context(client, db_session)
    created = create_item(client, context)
    item_id = created.json()["id"]
    receive(client, context, item_id, 5)

    response = client.delete(
        f"/inventory/items/{item_id}",
        headers=context["headers"],
    )

    assert response.status_code == 400


def test_missing_inventory_item_returns_404(client, db_session):
    context = setup_inventory_context(client, db_session)

    response = client.get(
        "/inventory/items/999999",
        headers=context["headers"],
    )

    assert response.status_code == 404
