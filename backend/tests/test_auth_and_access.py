from datetime import datetime

from backend.database import crud
from backend.tests.conftest import make_user


def test_register_requires_terms_acceptance(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "no_terms",
            "email": "no_terms@example.com",
            "password": "password123",
            "terms_accepted": False,
        },
    )

    assert response.status_code == 400
    assert "terms" in response.json()["detail"].lower()


def test_register_creates_pregnant_mother_user(client, monkeypatch):
    created_user = make_user(
        user_id=11,
        username="new_mother",
        email="new_mother@example.com",
        registration_date=datetime.utcnow(),
        terms_accepted=True,
        terms_accepted_at=datetime.utcnow(),
    )

    monkeypatch.setattr(crud, "get_user_by_email", lambda db, email: None)
    monkeypatch.setattr(crud, "get_user_by_username", lambda db, username: None)
    monkeypatch.setattr(crud, "create_user", lambda **kwargs: created_user)
    monkeypatch.setattr(crud, "create_system_log", lambda **kwargs: None)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "new_mother",
            "email": "new_mother@example.com",
            "password": "password123",
            "terms_accepted": True,
            "role": "system_admin",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "new_mother"
    assert data["role"] == "pregnant_mother"
    assert data["terms_accepted"] is True


def test_register_rejects_passwords_too_long_for_bcrypt(client, monkeypatch):
    monkeypatch.setattr(crud, "get_user_by_email", lambda db, email: None)
    monkeypatch.setattr(crud, "get_user_by_username", lambda db, username: None)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "long_password",
            "email": "long_password@example.com",
            "password": "a" * 73,
            "terms_accepted": True,
        },
    )

    assert response.status_code == 400
    assert "72 bytes" in response.json()["detail"]


def test_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_admin_stats_rejects_non_admin(authenticated_client):
    response = authenticated_client.get("/api/v1/admin/stats")

    assert response.status_code == 403
    assert "role" in response.json()["detail"].lower()


def test_change_password_validates_current_password(authenticated_client, monkeypatch):
    from backend.api.routes import auth

    monkeypatch.setattr(auth, "verify_password", lambda plain, hashed: False)

    response = authenticated_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpass", "new_password": "newpass123"},
    )

    assert response.status_code == 400
    assert "current password" in response.json()["detail"].lower()
