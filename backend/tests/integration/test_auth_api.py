from datetime import datetime, timedelta, timezone

import jwt

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.api.auth import auth_rate_limit
from app.core.config import get_settings


def registration_payload(**changes):
    payload = {
        "name": "Alex Owner",
        "email": "alex@example.com",
        "password": "correct-horse-battery-staple",
    }
    payload.update(changes)
    return payload


def test_register_login_and_read_current_user(client, db):
    registered = client.post("/api/auth/register", json=registration_payload())
    assert registered.status_code == 201
    assert registered.json()["token_type"] == "bearer"
    assert registered.json()["refresh_token"]
    assert registered.json()["user"]["email"] == "alex@example.com"
    stored_user = db.query(User).filter_by(email="alex@example.com").one()
    assert stored_user.password_hash != "correct-horse-battery-staple"
    assert stored_user.password_hash.startswith("pbkdf2_sha256$")

    login = client.post(
        "/api/auth/login",
        json={
            "email": "ALEX@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    current = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current.status_code == 200
    assert current.json()["name"] == "Alex Owner"
    assert current.json()["role"] == "owner"


def test_registration_rejects_duplicate_email(client):
    assert client.post("/api/auth/register", json=registration_payload()).status_code == 201

    duplicate = client.post("/api/auth/register", json=registration_payload())

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email is already registered"


def test_registration_rejects_blank_name(client):
    response = client.post(
        "/api/auth/register", json=registration_payload(name="   ")
    )

    assert response.status_code == 422


def test_login_rejects_bad_credentials_without_revealing_email_state(client):
    client.post("/api/auth/register", json=registration_payload())

    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "alex@example.com", "password": "wrong-password"},
    )
    unknown_email = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_current_user_requires_a_valid_bearer_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid"}
    ).status_code == 401


def test_access_token_rejects_expired_wrong_signature_and_wrong_type(client):
    registered = client.post("/api/auth/register", json=registration_payload())
    user_id = registered.json()["user"]["id"]
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    wrong_signature = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "access",
        },
        "not-the-application-secret",
        algorithm="HS256",
    )
    wrong_type = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "refresh",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    for token in (expired, wrong_signature, wrong_type):
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired access token"


def test_login_rate_limit_returns_retry_after(client):
    original_limit = auth_rate_limit.limit
    auth_rate_limit.limit = 2
    try:
        for _ in range(2):
            response = client.post(
                "/api/auth/login",
                json={"email": "missing@example.com", "password": "wrong-password"},
            )
            assert response.status_code == 401

        blocked = client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
    finally:
        auth_rate_limit.limit = original_limit

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many requests"}
    assert int(blocked.headers["Retry-After"]) >= 1


def test_refresh_tokens_rotate_and_cannot_be_reused(client, db):
    registered = client.post("/api/auth/register", json=registration_payload())
    first_refresh_token = registered.json()["refresh_token"]
    stored_token = db.query(RefreshToken).one()
    assert stored_token.token_hash != first_refresh_token

    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": first_refresh_token}
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["refresh_token"] != first_refresh_token
    reused = client.post(
        "/api/auth/refresh", json={"refresh_token": first_refresh_token}
    )
    assert reused.status_code == 401
    assert reused.json()["detail"] == "Invalid or expired refresh token"


def test_logout_revokes_refresh_token(client):
    registered = client.post("/api/auth/register", json=registration_payload())
    refresh_token = registered.json()["refresh_token"]

    logged_out = client.post(
        "/api/auth/logout", json={"refresh_token": refresh_token}
    )
    rejected = client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert logged_out.status_code == 204
    assert rejected.status_code == 401
