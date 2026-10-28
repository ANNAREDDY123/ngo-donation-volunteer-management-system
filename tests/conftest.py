
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app

# Import all models so SQLAlchemy registers their tables.
from app.models import Donor, User


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def db_session(client):
    """Provide a session connected to the client's isolated test database."""
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)

    try:
        yield db
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


@pytest.fixture
def registered_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "donor@example.com",
            "full_name": "Test Donor",
            "password": "SecurePass123!",
            "role": "donor",
        },
    )

    assert response.status_code == 201
    return response.json()


@pytest.fixture
def access_token(client, registered_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "donor@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]
