import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.db.seed import seed_reference_data
from app.core.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limits():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as session:
        seed_reference_data(session)
        yield session


@pytest.fixture()
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Owner",
            "email": "owner@example.com",
            "password": "secure-password-123",
        },
    )
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    return client
