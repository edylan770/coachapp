def test_register_creates_trainer_profile(client, make_trainer):
    headers = make_trainer(email="coach@example.com")
    response = client.get("/trainers/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "coach"
    assert body["settings"] == {}


def test_register_accepts_explicit_display_name(client):
    client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "supersecret1", "display_name": "Coach X"},
    )
    tokens = client.post(
        "/auth/login", json={"email": "x@example.com", "password": "supersecret1"}
    ).json()
    me = client.get(
        "/trainers/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.json()["display_name"] == "Coach X"


def test_patch_trainer_profile(client, make_trainer):
    headers = make_trainer()
    response = client.patch(
        "/trainers/me",
        json={"display_name": "Big Coach", "bio": "20 years", "settings": {"units": "kg"}},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Big Coach"
    assert body["bio"] == "20 years"
    assert body["settings"] == {"units": "kg"}


def test_trainer_endpoints_require_auth(client):
    assert client.get("/trainers/me").status_code == 401
