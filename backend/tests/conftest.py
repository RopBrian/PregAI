import uuid
import os
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.api.main import app
from backend.api.routes.auth import get_current_user
from backend.database.database import get_db


class DummyDB:
    def commit(self):
        return None

    def refresh(self, obj):
        return None

    def delete(self, obj):
        return None

    def close(self):
        return None


@pytest.fixture
def db():
    return DummyDB()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mother_user():
    return SimpleNamespace(
        user_id=1,
        username="mother_user",
        email="mother@example.com",
        role="pregnant_mother",
        password_hash="hashed",
        images=[],
        sessions=[],
        conversations=[],
        predictions=[],
        logs=[],
    )


@pytest.fixture
def admin_user():
    return SimpleNamespace(
        user_id=2,
        username="admin_user",
        email="admin@example.com",
        role="system_admin",
        password_hash="hashed",
        images=[],
        sessions=[],
        conversations=[],
        predictions=[],
        logs=[],
    )


@pytest.fixture
def authenticated_client(client, mother_user):
    async def override_user():
        return mother_user

    app.dependency_overrides[get_current_user] = override_user
    return client


@pytest.fixture
def admin_client(client, admin_user):
    async def override_user():
        return admin_user

    app.dependency_overrides[get_current_user] = override_user
    return client


@pytest.fixture
def session_id():
    return uuid.uuid4()


def make_user(**overrides):
    data = {
        "user_id": 10,
        "username": "test_user",
        "email": "test@example.com",
        "role": "pregnant_mother",
        "password_hash": "hashed",
        "terms_accepted": True,
        "terms_accepted_at": None,
        "registration_date": None,
        "first_name": None,
        "last_name": None,
        "date_of_birth": None,
        "images": [],
        "sessions": [],
        "conversations": [],
        "predictions": [],
        "logs": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)
