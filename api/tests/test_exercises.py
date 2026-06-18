def test_global_library_is_seeded(client, make_trainer):
    headers = make_trainer()
    exercises = client.get("/exercises", headers=headers).json()
    names = {e["name"] for e in exercises}
    assert {"Back Squat", "Bench Press", "Deadlift"} <= names
    assert all(e["is_custom"] is False for e in exercises)


def test_create_custom_exercise(client, make_trainer):
    headers = make_trainer()
    response = client.post(
        "/exercises", json={"name": "Banded Squat", "description": "vs bands"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["is_custom"] is True
    names = [e["name"] for e in client.get("/exercises", headers=headers).json()]
    assert "Banded Squat" in names


def test_duplicate_custom_name_conflicts(client, make_trainer):
    headers = make_trainer()
    assert client.post("/exercises", json={"name": "Sled Push"}, headers=headers).status_code == 201
    assert client.post("/exercises", json={"name": "Sled Push"}, headers=headers).status_code == 409


def test_override_shadows_global(client, make_trainer):
    headers = make_trainer()
    library = client.get("/exercises", headers=headers).json()
    squat = next(e for e in library if e["name"] == "Back Squat")

    override = client.post(
        "/exercises",
        json={
            "name": "Back Squat (my cues)",
            "video_url": "https://example.com/squat",
            "parent_exercise_id": squat["id"],
        },
        headers=headers,
    )
    assert override.status_code == 201

    merged = client.get("/exercises", headers=headers).json()
    ids = {e["id"] for e in merged}
    assert squat["id"] not in ids  # shadowed
    assert override.json()["id"] in ids


def test_override_must_reference_global(client, make_trainer):
    headers = make_trainer()
    custom = client.post("/exercises", json={"name": "Custom A"}, headers=headers).json()
    response = client.post(
        "/exercises",
        json={"name": "Override of custom", "parent_exercise_id": custom["id"]},
        headers=headers,
    )
    assert response.status_code == 422


def test_globals_are_read_only(client, make_trainer):
    headers = make_trainer()
    squat = next(
        e for e in client.get("/exercises", headers=headers).json() if e["name"] == "Back Squat"
    )
    assert (
        client.patch(f"/exercises/{squat['id']}", json={"name": "Nope"}, headers=headers
        ).status_code == 403
    )
    assert client.delete(f"/exercises/{squat['id']}", headers=headers).status_code == 403


def test_update_and_delete_own_exercise(client, make_trainer):
    headers = make_trainer()
    created = client.post("/exercises", json={"name": "Yoke Carry"}, headers=headers).json()
    patched = client.patch(
        f"/exercises/{created['id']}", json={"description": "heavy"}, headers=headers
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "heavy"
    assert client.delete(f"/exercises/{created['id']}", headers=headers).status_code == 204


def test_tenancy_customs_invisible_across_trainers(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    created = client.post("/exercises", json={"name": "A Special"}, headers=headers_a).json()

    names_b = [e["name"] for e in client.get("/exercises", headers=headers_b).json()]
    assert "A Special" not in names_b
    assert client.get(f"/exercises/{created['id']}", headers=headers_b).status_code == 404
    assert (
        client.patch(f"/exercises/{created['id']}", json={"name": "Stolen"}, headers=headers_b
        ).status_code == 404
    )
    assert client.delete(f"/exercises/{created['id']}", headers=headers_b).status_code == 404
