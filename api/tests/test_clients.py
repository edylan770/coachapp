from datetime import UTC, datetime, timedelta


def invite(client, headers, email="athlete@example.com", full_name="Athlete A"):
    return client.post(
        "/clients", json={"email": email, "full_name": full_name}, headers=headers
    )


def accept(client, token, password="clientpass123"):
    return client.post("/auth/accept-invite", json={"token": token, "password": password})


def test_invite_returns_one_time_token(client, make_trainer):
    headers = make_trainer()
    response = invite(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "invited"
    assert body["has_account"] is False
    assert body["invite_token"]
    # The token is never returned again on plain reads.
    fetched = client.get(f"/clients/{body['id']}", headers=headers).json()
    assert "invite_token" not in fetched


def test_duplicate_invite_same_trainer_conflicts(client, make_trainer):
    headers = make_trainer()
    assert invite(client, headers).status_code == 201
    assert invite(client, headers).status_code == 409


def test_two_trainers_can_invite_same_email(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    assert invite(client, headers_a).status_code == 201
    assert invite(client, headers_b).status_code == 201


def test_accept_invite_creates_client_account(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()

    response = accept(client, invited["invite_token"])
    assert response.status_code == 201
    tokens = response.json()

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ).json()
    assert me["role"] == "client"
    assert me["email"] == "athlete@example.com"

    refreshed = client.get(f"/clients/{invited['id']}", headers=headers).json()
    assert refreshed["status"] == "active"
    assert refreshed["has_account"] is True


def test_invite_token_single_use(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    assert accept(client, invited["invite_token"]).status_code == 201
    assert accept(client, invited["invite_token"]).status_code == 400


def test_expired_invite_rejected(client, make_trainer, db_session):
    from app.models.client import Client

    headers = make_trainer()
    invited = invite(client, headers).json()
    row = db_session.query(Client).filter_by(id=invited["id"]).one()
    row.invite_expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    assert accept(client, invited["invite_token"]).status_code == 400


def test_reinvite_rotates_token(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    reinvited = client.post(f"/clients/{invited['id']}/reinvite", headers=headers).json()
    assert reinvited["invite_token"] != invited["invite_token"]
    assert accept(client, invited["invite_token"]).status_code == 400
    assert accept(client, reinvited["invite_token"]).status_code == 201


def test_reinvite_after_acceptance_conflicts(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    accept(client, invited["invite_token"])
    assert client.post(f"/clients/{invited['id']}/reinvite", headers=headers).status_code == 409


def test_status_patch_rules(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()

    # Cannot activate/pause before the invite is accepted.
    response = client.patch(
        f"/clients/{invited['id']}", json={"status": "paused"}, headers=headers
    )
    assert response.status_code == 409

    accept(client, invited["invite_token"])
    paused = client.patch(
        f"/clients/{invited['id']}", json={"status": "paused"}, headers=headers
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"


def test_email_locked_after_acceptance(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    ok = client.patch(
        f"/clients/{invited['id']}", json={"email": "new@example.com"}, headers=headers
    )
    assert ok.status_code == 200
    assert ok.json()["email"] == "new@example.com"

    reinvited = client.post(f"/clients/{invited['id']}/reinvite", headers=headers).json()
    accept(client, reinvited["invite_token"])
    locked = client.patch(
        f"/clients/{invited['id']}", json={"email": "other@example.com"}, headers=headers
    )
    assert locked.status_code == 409


def test_delete_client_removes_account(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    accept(client, invited["invite_token"], password="clientpass123")

    assert client.delete(f"/clients/{invited['id']}", headers=headers).status_code == 204
    assert client.get(f"/clients/{invited['id']}", headers=headers).status_code == 404
    login = client.post(
        "/auth/login", json={"email": "athlete@example.com", "password": "clientpass123"}
    )
    assert login.status_code == 401


def test_list_clients_filters_by_status(client, make_trainer):
    headers = make_trainer()
    first = invite(client, headers, email="one@example.com", full_name="One").json()
    invite(client, headers, email="two@example.com", full_name="Two")
    accept(client, first["invite_token"])

    everyone = client.get("/clients", headers=headers).json()
    assert len(everyone) == 2
    active = client.get("/clients", params={"status_filter": "active"}, headers=headers).json()
    assert [c["email"] for c in active] == ["one@example.com"]


def test_client_role_cannot_use_trainer_endpoints(client, make_trainer):
    headers = make_trainer()
    invited = invite(client, headers).json()
    tokens = accept(client, invited["invite_token"]).json()
    client_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/clients", headers=client_headers).status_code == 403
    assert client.get("/programs", headers=client_headers).status_code == 403


def test_tenancy_clients_are_invisible_across_trainers(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    invited = invite(client, headers_a).json()

    assert client.get(f"/clients/{invited['id']}", headers=headers_b).status_code == 404
    patched = client.patch(
        f"/clients/{invited['id']}", json={"full_name": "Hijack"}, headers=headers_b
    )
    assert patched.status_code == 404
    assert client.delete(f"/clients/{invited['id']}", headers=headers_b).status_code == 404
    assert len(client.get("/clients", headers=headers_b).json()) == 0
