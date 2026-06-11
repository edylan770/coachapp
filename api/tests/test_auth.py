import uuid

from app import security

EMAIL = "coach@example.com"
PASSWORD = "supersecret1"


def register(client, email=EMAIL, password=PASSWORD, **extra):
    return client.post("/auth/register", json={"email": email, "password": password, **extra})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# --- register ---


def test_register_creates_trainer(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert body["role"] == "trainer"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_register_normalizes_email_and_rejects_duplicates(client):
    assert register(client, email="Coach@Example.com ").status_code == 201
    response = register(client, email="coach@example.com")
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    assert register(client, password="short1").status_code == 422


def test_register_ignores_role_injection(client):
    # Clients are invite-only; a role field in the payload must not be honored.
    response = register(client, role="client")
    assert response.status_code == 201
    assert response.json()["role"] == "trainer"


# --- login ---


def test_login_returns_token_pair(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"] and body["refresh_token"]


def test_login_rejects_bad_credentials_uniformly(client):
    register(client)
    wrong_password = login(client, password="not-the-password")
    unknown_email = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_inactive_user_cannot_login_or_use_token(client, db_session):
    from app.models.user import User

    register(client)
    access = login(client).json()["access_token"]

    user = db_session.query(User).filter_by(email=EMAIL).one()
    user.is_active = False
    db_session.commit()

    assert login(client).status_code == 401
    assert client.get("/auth/me", headers=auth_header(access)).status_code == 401


# --- /auth/me & access tokens ---


def test_me_returns_current_user(client):
    register(client)
    access = login(client).json()["access_token"]
    response = client.get("/auth/me", headers=auth_header(access))
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth_header("garbage")).status_code == 401


def test_me_rejects_refresh_token_as_access_token(client):
    register(client)
    refresh_token = login(client).json()["refresh_token"]
    assert client.get("/auth/me", headers=auth_header(refresh_token)).status_code == 401


def test_expired_access_token_rejected(client):
    user_id = uuid.UUID(register(client).json()["id"])
    expired = security.create_access_token(user_id, "trainer", ttl_minutes=-1)
    assert client.get("/auth/me", headers=auth_header(expired)).status_code == 401


# --- refresh rotation & revocation ---


def test_refresh_rotates_and_new_access_token_works(client):
    register(client)
    first = login(client).json()
    response = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    me = client.get("/auth/me", headers=auth_header(second["access_token"]))
    assert me.status_code == 200


def test_refresh_reuse_revokes_token_family(client):
    register(client)
    first = login(client).json()
    second = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).json()

    # Reusing the rotated (now revoked) token is treated as theft...
    reuse = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401

    # ...so the still-newest token is revoked too.
    after = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert after.status_code == 401


def test_unknown_refresh_token_rejected(client):
    response = client.post("/auth/refresh", json={"refresh_token": "never-issued"})
    assert response.status_code == 401


def test_logout_revokes_refresh_token_idempotently(client):
    register(client)
    refresh_token = login(client).json()["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204
    refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 401
    # Idempotent: logging out again (or with an unknown token) is still 204.
    logout_again = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_again.status_code == 204
