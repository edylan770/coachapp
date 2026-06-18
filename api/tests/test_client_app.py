import io
import uuid
from datetime import date

import pytest


@pytest.fixture()
def setup(client, make_trainer):
    """Trainer with an accepted client and an assigned program; returns
    (trainer_headers, client_headers, client_id, program_tree)."""
    trainer_headers = make_trainer()
    invited = client.post(
        "/clients",
        json={"email": "athlete@example.com", "full_name": "Athlete"},
        headers=trainer_headers,
    ).json()
    tokens = client.post(
        "/auth/accept-invite", json={"token": invited["invite_token"], "password": "clientpass1"}
    ).json()
    client_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    exercises = client.get("/exercises", headers=trainer_headers).json()
    squat = next(e["id"] for e in exercises if e["name"] == "Back Squat")
    program = client.post(
        "/programs",
        json={"name": "Base", "client_id": invited["id"], "starts_on": "2026-06-01"},
        headers=trainer_headers,
    ).json()
    tree = client.put(
        f"/programs/{program['id']}/structure",
        json={
            "blocks": [
                {
                    "name": "Block 1",
                    "weeks": [
                        {
                            "days": [
                                {
                                    "name": "Day 1",
                                    "prescriptions": [
                                        {
                                            "exercise_id": squat,
                                            "sets": 3,
                                            "rep_scheme": {"type": "fixed", "reps": 5},
                                            "load_scheme": {"type": "rpe", "rpe": 8},
                                            "rest_seconds": 180,
                                        }
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ]
        },
        headers=trainer_headers,
    ).json()
    return trainer_headers, client_headers, invited["id"], tree


def make_log_payload(tree, *, log_id=None, set_id=None, reps=5):
    day = tree["blocks"][0]["weeks"][0]["days"][0]
    rx = day["prescriptions"][0]
    return {
        "id": log_id or str(uuid.uuid4()),
        "program_day_id": day["id"],
        "workout_date": str(date(2026, 6, 1)),
        "completed_at": "2026-06-01T18:00:00Z",
        "set_logs": [
            {
                "id": set_id or str(uuid.uuid4()),
                "prescription_id": rx["id"],
                "exercise_id": rx["exercise_id"],
                "exercise_name": "Back Squat",
                "position": 0,
                "set_number": 1,
                "weight": 140,
                "weight_unit": "kg",
                "reps": reps,
                "rpe": 8,
                "prescribed_snapshot": {
                    "sets": rx["sets"],
                    "rep_scheme": rx["rep_scheme"],
                    "load_scheme": rx["load_scheme"],
                },
            }
        ],
    }


# --- /me/program ---


def test_client_sees_assigned_program_with_exercises(client, setup):
    _, client_headers, _, _ = setup
    response = client.get("/me/program", headers=client_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["program"]["name"] == "Base"
    assert body["program"]["starts_on"] == "2026-06-01"
    names = [e["name"] for e in body["exercises"]]
    assert names == ["Back Squat"]


def test_client_without_program_gets_404(client, make_trainer):
    headers = make_trainer()
    invited = client.post(
        "/clients", json={"email": "x@example.com", "full_name": "X"}, headers=headers
    ).json()
    tokens = client.post(
        "/auth/accept-invite", json={"token": invited["invite_token"], "password": "clientpass1"}
    ).json()
    response = client.get(
        "/me/program", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 404


def test_trainer_cannot_use_client_endpoints(client, setup):
    trainer_headers, _, _, _ = setup
    assert client.get("/me/program", headers=trainer_headers).status_code == 403
    assert (
        client.post("/me/sync", json={"workout_logs": []}, headers=trainer_headers).status_code
        == 403
    )


# --- sync ---


def test_sync_creates_then_updates_idempotently(client, setup):
    _, client_headers, _, tree = setup
    payload = make_log_payload(tree)

    first = client.post("/me/sync", json={"workout_logs": [payload]}, headers=client_headers)
    assert first.status_code == 200
    assert first.json()["results"] == [{"id": payload["id"], "status": "created", "detail": None}]

    payload["set_logs"][0]["reps"] = 4  # client edited before re-sync
    second = client.post("/me/sync", json={"workout_logs": [payload]}, headers=client_headers)
    assert second.json()["results"][0]["status"] == "updated"

    logs = client.get("/me/workout-logs", headers=client_headers).json()
    assert len(logs) == 1
    assert logs[0]["set_logs"][0]["reps"] == 4
    assert logs[0]["set_logs"][0]["prescription_id"] is not None


def test_sync_rejects_foreign_log_id_without_blocking_batch(client, setup, make_trainer):
    _, client_headers, _, tree = setup
    # A second trainer's client logs a workout...
    other_trainer = make_trainer(email="other@example.com")
    other_invited = client.post(
        "/clients",
        json={"email": "other-ath@example.com", "full_name": "Other"},
        headers=other_trainer,
    ).json()
    other_tokens = client.post(
        "/auth/accept-invite",
        json={"token": other_invited["invite_token"], "password": "clientpass1"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    stolen = make_log_payload(tree)
    stolen["program_day_id"] = None
    stolen["set_logs"] = []
    assert (
        client.post("/me/sync", json={"workout_logs": [stolen]}, headers=other_headers)
        .json()["results"][0]["status"]
        == "created"
    )

    # ...the first client tries to reuse that id; the good item still lands.
    good = make_log_payload(tree)
    hijack = make_log_payload(tree, log_id=stolen["id"])
    response = client.post(
        "/me/sync", json={"workout_logs": [hijack, good]}, headers=client_headers
    ).json()
    statuses = {r["id"]: r["status"] for r in response["results"]}
    assert statuses[stolen["id"]] == "rejected"
    assert statuses[good["id"]] == "created"

    # The other client's log is untouched.
    other_logs = client.get("/me/workout-logs", headers=other_headers).json()
    assert [log["id"] for log in other_logs] == [stolen["id"]]


def test_sync_nullifies_stale_references_but_keeps_snapshot(client, setup):
    trainer_headers, client_headers, _, tree = setup
    payload = make_log_payload(tree)

    # Trainer wipes the program structure before the client gets to sync.
    program_id = tree["id"]
    assert (
        client.put(
            f"/programs/{program_id}/structure", json={"blocks": []}, headers=trainer_headers
        ).status_code
        == 200
    )

    response = client.post(
        "/me/sync", json={"workout_logs": [payload]}, headers=client_headers
    ).json()
    assert response["results"][0]["status"] == "created"
    log = client.get("/me/workout-logs", headers=client_headers).json()[0]
    assert log["program_day_id"] is None
    set_log = log["set_logs"][0]
    assert set_log["prescription_id"] is None
    assert set_log["exercise_id"] is not None  # global exercise still exists
    assert set_log["exercise_name"] == "Back Squat"
    assert set_log["prescribed_snapshot"]["rep_scheme"] == {"type": "fixed", "reps": 5}


def test_sync_rejects_invalid_item_independently(client, setup):
    _, client_headers, _, tree = setup
    good = make_log_payload(tree)
    # Force a uniqueness violation: set id reused across two different logs.
    clash = make_log_payload(tree, set_id=good["set_logs"][0]["id"])
    response = client.post(
        "/me/sync", json={"workout_logs": [good, clash]}, headers=client_headers
    ).json()
    statuses = [r["status"] for r in response["results"]]
    assert statuses == ["created", "rejected"]
    assert len(client.get("/me/workout-logs", headers=client_headers).json()) == 1


def test_trainer_reads_client_logs(client, setup):
    trainer_headers, client_headers, client_id, tree = setup
    payload = make_log_payload(tree)
    client.post("/me/sync", json={"workout_logs": [payload]}, headers=client_headers)

    logs = client.get(f"/clients/{client_id}/workout-logs", headers=trainer_headers).json()
    assert len(logs) == 1
    assert logs[0]["set_logs"][0]["weight"] == 140


def test_other_trainer_cannot_read_logs(client, setup, make_trainer):
    _, client_headers, client_id, tree = setup
    client.post(
        "/me/sync", json={"workout_logs": [make_log_payload(tree)]}, headers=client_headers
    )
    other = make_trainer(email="other@example.com")
    assert client.get(f"/clients/{client_id}/workout-logs", headers=other).status_code == 404


# --- check-ins ---


def upload_photo(client, headers, content=b"\xff\xd8\xff fake jpeg"):
    return client.post(
        "/me/check-ins/photos",
        files={"file": ("front.jpg", io.BytesIO(content), "image/jpeg")},
        headers=headers,
    )


def test_check_in_flow_with_photo(client, setup):
    trainer_headers, client_headers, client_id, _ = setup
    upload = upload_photo(client, client_headers)
    assert upload.status_code == 200
    key = upload.json()["key"]

    response = client.post(
        "/me/check-ins",
        json={
            "check_in_date": "2026-06-12",
            "weight": 82.4,
            "weight_unit": "kg",
            "measurements": {"waist": 81.0},
            "photos": [key],
            "adherence": {"training": 5, "nutrition": 3, "sleep": 4},
            "notes": "Felt strong, slept badly midweek.",
        },
        headers=client_headers,
    )
    assert response.status_code == 201, response.text
    check_in = response.json()
    assert check_in["photos"] == [key]
    assert check_in["adherence"] == {"training": 5, "nutrition": 3, "sleep": 4}

    # Trainer sees it and can fetch the photo; the client can too.
    listed = client.get(f"/clients/{client_id}/check-ins", headers=trainer_headers).json()
    assert len(listed) == 1
    assert client.get(f"/files/{key}", headers=trainer_headers).status_code == 200
    assert client.get(f"/files/{key}", headers=client_headers).status_code == 200


def test_check_in_idempotent_retry_and_duplicate_date(client, setup):
    _, client_headers, _, _ = setup
    check_in_id = str(uuid.uuid4())
    body = {"id": check_in_id, "check_in_date": "2026-06-12", "weight": 80}
    first = client.post("/me/check-ins", json=body, headers=client_headers)
    assert first.status_code == 201
    retry = client.post("/me/check-ins", json=body, headers=client_headers)
    assert retry.status_code == 200
    assert retry.json()["id"] == check_in_id

    duplicate_date = client.post(
        "/me/check-ins",
        json={"check_in_date": "2026-06-12", "weight": 81},
        headers=client_headers,
    )
    assert duplicate_date.status_code == 409


def test_check_in_rejects_foreign_photo_keys(client, setup, make_trainer):
    _, client_headers, _, _ = setup
    other_trainer = make_trainer(email="other@example.com")
    other_invited = client.post(
        "/clients", json={"email": "o@example.com", "full_name": "O"}, headers=other_trainer
    ).json()
    other_tokens = client.post(
        "/auth/accept-invite",
        json={"token": other_invited["invite_token"], "password": "clientpass1"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    foreign_key = upload_photo(client, other_headers).json()["key"]

    response = client.post(
        "/me/check-ins",
        json={"check_in_date": "2026-06-12", "photos": [foreign_key]},
        headers=client_headers,
    )
    assert response.status_code == 422


def test_photo_upload_rejects_bad_type(client, setup):
    _, client_headers, _, _ = setup
    response = client.post(
        "/me/check-ins/photos",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=client_headers,
    )
    assert response.status_code == 422


def test_photo_access_denied_for_strangers(client, setup, make_trainer):
    _, client_headers, _, _ = setup
    key = upload_photo(client, client_headers).json()["key"]
    other_trainer = make_trainer(email="stranger@example.com")
    assert client.get(f"/files/{key}", headers=other_trainer).status_code == 404
    assert client.get(f"/files/{key}").status_code == 401
