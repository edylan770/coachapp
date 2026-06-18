import pytest


@pytest.fixture()
def exercise_ids(client, make_trainer):
    """Headers for a trainer plus a couple of global exercise ids."""
    headers = make_trainer()
    library = client.get("/exercises", headers=headers).json()
    by_name = {e["name"]: e["id"] for e in library}
    return headers, by_name


def make_structure(squat_id, bench_id):
    return {
        "blocks": [
            {
                "name": "Block 1",
                "weeks": [
                    {
                        "name": "Week 1",
                        "days": [
                            {
                                "name": "Day 1",
                                "prescriptions": [
                                    {
                                        "exercise_id": squat_id,
                                        "sets": 5,
                                        "rep_scheme": {"type": "fixed", "reps": 5},
                                        "load_scheme": {"type": "percent_1rm", "percent": 80},
                                        "rest_seconds": 180,
                                    },
                                    {
                                        "exercise_id": bench_id,
                                        "sets": 3,
                                        "rep_scheme": {"type": "range", "min": 8, "max": 12},
                                        "load_scheme": {"type": "rir", "rir": 2},
                                        "tempo": "31X0",
                                    },
                                ],
                            },
                            {"name": "Day 2", "is_rest_day": True, "prescriptions": []},
                        ],
                    }
                ],
            }
        ]
    }


def create_program(client, headers, name="Strength Base", **extra):
    return client.post("/programs", json={"name": name, **extra}, headers=headers)


def test_create_and_get_program(client, exercise_ids):
    headers, _ = exercise_ids
    created = create_program(client, headers)
    assert created.status_code == 201
    body = created.json()
    assert body["version"] == 1
    assert body["blocks"] == []

    listed = client.get("/programs", headers=headers).json()
    assert [p["name"] for p in listed] == ["Strength Base"]


def test_put_structure_builds_tree(client, exercise_ids):
    headers, ex = exercise_ids
    program = create_program(client, headers).json()
    structure = make_structure(ex["Back Squat"], ex["Bench Press"])

    response = client.put(
        f"/programs/{program['id']}/structure", json=structure, headers=headers
    )
    assert response.status_code == 200, response.text
    tree = response.json()
    assert len(tree["blocks"]) == 1
    week = tree["blocks"][0]["weeks"][0]
    assert [d["name"] for d in week["days"]] == ["Day 1", "Day 2"]
    day1 = week["days"][0]
    assert [p["position"] for p in day1["prescriptions"]] == [0, 1]
    assert day1["prescriptions"][0]["rep_scheme"] == {"type": "fixed", "reps": 5}
    assert day1["prescriptions"][1]["load_scheme"] == {"type": "rir", "rir": 2}
    assert week["days"][1]["is_rest_day"] is True


def test_put_structure_upsert_preserves_ids_and_reorders(client, exercise_ids):
    headers, ex = exercise_ids
    program = create_program(client, headers).json()
    tree = client.put(
        f"/programs/{program['id']}/structure",
        json=make_structure(ex["Back Squat"], ex["Bench Press"]),
        headers=headers,
    ).json()

    day1 = tree["blocks"][0]["weeks"][0]["days"][0]
    squat_rx, bench_rx = day1["prescriptions"]

    # Round-trip the tree, swapping the two prescriptions and editing sets.
    edited = {
        "blocks": [
            {
                "id": tree["blocks"][0]["id"],
                "name": "Block 1 renamed",
                "weeks": [
                    {
                        "id": tree["blocks"][0]["weeks"][0]["id"],
                        "name": "Week 1",
                        "days": [
                            {
                                "id": day1["id"],
                                "name": "Day 1",
                                "prescriptions": [
                                    {**bench_rx, "sets": 4},
                                    {**squat_rx},
                                ],
                            }
                            # Day 2 omitted -> deleted
                        ],
                    }
                ],
            }
        ]
    }
    response = client.put(
        f"/programs/{program['id']}/structure", json=edited, headers=headers
    )
    assert response.status_code == 200, response.text
    new_tree = response.json()
    block = new_tree["blocks"][0]
    assert block["id"] == tree["blocks"][0]["id"]
    assert block["name"] == "Block 1 renamed"
    days = block["weeks"][0]["days"]
    assert len(days) == 1  # rest day removed
    rx = days[0]["prescriptions"]
    # Same rows, new order, edit applied.
    assert [p["id"] for p in rx] == [bench_rx["id"], squat_rx["id"]]
    assert rx[0]["sets"] == 4
    assert [p["position"] for p in rx] == [0, 1]


def test_put_structure_rejects_foreign_child_id(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    ex_a = client.get("/exercises", headers=headers_a).json()
    squat = next(e["id"] for e in ex_a if e["name"] == "Back Squat")

    program_a = create_program(client, headers_a).json()
    tree_a = client.put(
        f"/programs/{program_a['id']}/structure",
        json=make_structure(squat, squat),
        headers=headers_a,
    )
    # same exercise twice in one day is allowed; we only need a block id
    block_id_a = tree_a.json()["blocks"][0]["id"]

    program_b = create_program(client, headers_b).json()
    hijack = {"blocks": [{"id": block_id_a, "name": "Steal", "weeks": []}]}
    response = client.put(
        f"/programs/{program_b['id']}/structure", json=hijack, headers=headers_b
    )
    assert response.status_code == 422


def test_put_structure_rejects_foreign_exercise(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    custom_a = client.post("/exercises", json={"name": "A Secret"}, headers=headers_a).json()

    program_b = create_program(client, headers_b).json()
    structure = {
        "blocks": [
            {
                "name": "B",
                "weeks": [
                    {
                        "days": [
                            {
                                "prescriptions": [
                                    {
                                        "exercise_id": custom_a["id"],
                                        "sets": 3,
                                        "rep_scheme": {"type": "amrap"},
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
    }
    response = client.put(
        f"/programs/{program_b['id']}/structure", json=structure, headers=headers_b
    )
    assert response.status_code == 422


def test_invalid_scheme_rejected(client, exercise_ids):
    headers, ex = exercise_ids
    program = create_program(client, headers).json()
    bad = {
        "blocks": [
            {
                "name": "B",
                "weeks": [
                    {
                        "days": [
                            {
                                "prescriptions": [
                                    {
                                        "exercise_id": ex["Back Squat"],
                                        "sets": 3,
                                        "rep_scheme": {"type": "range", "min": 12, "max": 8},
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
    }
    response = client.put(f"/programs/{program['id']}/structure", json=bad, headers=headers)
    assert response.status_code == 422


def test_exercise_in_use_cannot_be_deleted(client, exercise_ids):
    headers, ex = exercise_ids
    custom = client.post("/exercises", json={"name": "My Squat"}, headers=headers).json()
    program = create_program(client, headers).json()
    client.put(
        f"/programs/{program['id']}/structure",
        json=make_structure(custom["id"], ex["Bench Press"]),
        headers=headers,
    )
    assert client.delete(f"/exercises/{custom['id']}", headers=headers).status_code == 409
    # Removing the program frees it.
    client.delete(f"/programs/{program['id']}", headers=headers)
    assert client.delete(f"/exercises/{custom['id']}", headers=headers).status_code == 204


def test_duplicate_program_deep_copies(client, exercise_ids):
    headers, ex = exercise_ids
    program = create_program(client, headers).json()
    client.put(
        f"/programs/{program['id']}/structure",
        json=make_structure(ex["Back Squat"], ex["Bench Press"]),
        headers=headers,
    )

    response = client.post(f"/programs/{program['id']}/duplicate", json={}, headers=headers)
    assert response.status_code == 201
    copy = response.json()
    assert copy["name"] == "Strength Base (copy)"
    assert copy["version"] == 2
    assert copy["source_program_id"] == program["id"]
    original = client.get(f"/programs/{program['id']}", headers=headers).json()
    assert len(copy["blocks"]) == len(original["blocks"]) == 1
    copy_rx = copy["blocks"][0]["weeks"][0]["days"][0]["prescriptions"]
    orig_rx = original["blocks"][0]["weeks"][0]["days"][0]["prescriptions"]
    assert len(copy_rx) == len(orig_rx) == 2
    assert {p["id"] for p in copy_rx}.isdisjoint({p["id"] for p in orig_rx})


def test_save_as_template_and_assign_flow(client, make_trainer):
    headers = make_trainer()
    invited = client.post(
        "/clients", json={"email": "ath@example.com", "full_name": "Ath"}, headers=headers
    ).json()
    client.post(
        "/auth/accept-invite", json={"token": invited["invite_token"], "password": "clientpass1"}
    )

    program = create_program(client, headers).json()
    template = client.post(
        f"/programs/{program['id']}/duplicate",
        json={"as_template": True, "name": "Base Template"},
        headers=headers,
    ).json()
    assert template["is_template"] is True
    assert template["client_id"] is None

    assigned = client.post(
        f"/programs/{template['id']}/duplicate",
        json={"name": "Ath's Block", "client_id": invited["id"]},
        headers=headers,
    ).json()
    assert assigned["client_id"] == invited["id"]
    assert assigned["is_template"] is False

    mine = client.get("/programs", params={"client_id": invited["id"]}, headers=headers).json()
    assert [p["name"] for p in mine] == ["Ath's Block"]
    templates = client.get("/programs", params={"is_template": True}, headers=headers).json()
    assert [p["name"] for p in templates] == ["Base Template"]


def test_template_cannot_have_client(client, make_trainer):
    headers = make_trainer()
    invited = client.post(
        "/clients", json={"email": "c@example.com", "full_name": "C"}, headers=headers
    ).json()
    response = create_program(
        client, headers, name="Bad", is_template=True, client_id=invited["id"]
    )
    assert response.status_code == 422

    program = create_program(client, headers, name="P").json()
    patched = client.patch(
        f"/programs/{program['id']}",
        json={"is_template": True, "client_id": invited["id"]},
        headers=headers,
    )
    assert patched.status_code == 422


def test_assign_and_unassign_via_patch(client, make_trainer):
    headers = make_trainer()
    invited = client.post(
        "/clients", json={"email": "c@example.com", "full_name": "C"}, headers=headers
    ).json()
    program = create_program(client, headers).json()

    assigned = client.patch(
        f"/programs/{program['id']}", json={"client_id": invited["id"]}, headers=headers
    )
    assert assigned.status_code == 200
    assert assigned.json()["client_id"] == invited["id"]

    unassigned = client.patch(
        f"/programs/{program['id']}", json={"client_id": None}, headers=headers
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["client_id"] is None


def test_cannot_assign_other_trainers_client(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    client_a = client.post(
        "/clients", json={"email": "c@example.com", "full_name": "C"}, headers=headers_a
    ).json()
    program_b = create_program(client, headers_b).json()
    response = client.patch(
        f"/programs/{program_b['id']}", json={"client_id": client_a["id"]}, headers=headers_b
    )
    assert response.status_code == 422


def test_tenancy_programs_invisible_across_trainers(client, make_trainer):
    headers_a = make_trainer(email="a@example.com")
    headers_b = make_trainer(email="b@example.com")
    program_a = create_program(client, headers_a).json()

    assert client.get(f"/programs/{program_a['id']}", headers=headers_b).status_code == 404
    assert (
        client.patch(f"/programs/{program_a['id']}", json={"name": "X"}, headers=headers_b
        ).status_code == 404
    )
    assert (
        client.put(
            f"/programs/{program_a['id']}/structure", json={"blocks": []}, headers=headers_b
        ).status_code == 404
    )
    assert (
        client.post(f"/programs/{program_a['id']}/duplicate", json={}, headers=headers_b
        ).status_code == 404
    )
    assert client.delete(f"/programs/{program_a['id']}", headers=headers_b).status_code == 404
    assert client.get("/programs", headers=headers_b).json() == []


def test_delete_client_unassigns_program(client, make_trainer):
    headers = make_trainer()
    invited = client.post(
        "/clients", json={"email": "c@example.com", "full_name": "C"}, headers=headers
    ).json()
    program = create_program(client, headers).json()
    client.patch(f"/programs/{program['id']}", json={"client_id": invited["id"]}, headers=headers)

    client.delete(f"/clients/{invited['id']}", headers=headers)
    survivor = client.get(f"/programs/{program['id']}", headers=headers)
    assert survivor.status_code == 200
    assert survivor.json()["client_id"] is None
