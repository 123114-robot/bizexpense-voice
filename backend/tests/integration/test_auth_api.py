from app.models.user import User


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
