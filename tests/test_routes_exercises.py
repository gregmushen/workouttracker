from app.repositories.exercises import ExerciseRepository


def _seed(db, name="Bench Press", **kwargs):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name,
                       equipment="barbell", category="strength", **kwargs)


def test_search_exercises(client, db):
    _seed(db, "Barbell Squat")
    _seed(db, "Leg Press")
    r = client.get("/exercises/search?q=squat")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Barbell Squat"


def test_get_exercise(client, db):
    eid = _seed(db)
    r = client.get(f"/exercises/{eid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Bench Press"


def test_get_exercise_404(client):
    r = client.get("/exercises/9999")
    assert r.status_code == 404


def test_create_exercise(client, db):
    ExerciseRepository(db).ensure_fts()
    r = client.post("/exercises", json={
        "name": "Custom Row",
        "source": "custom",
        "equipment": "barbell",
        "category": "strength",
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Custom Row"


def test_update_exercise(client, db):
    eid = _seed(db)
    r = client.patch(f"/exercises/{eid}", json={"equipment": "dumbbell"})
    assert r.status_code == 200
    assert r.json()["equipment"] == "dumbbell"


def test_delete_exercise(client, db):
    eid = _seed(db)
    r = client.delete(f"/exercises/{eid}")
    assert r.status_code == 204


def test_add_alias(client, db):
    eid = _seed(db, "Overhead Press")
    r = client.post(f"/exercises/{eid}/aliases", json={"alias": "ohp"})
    assert r.status_code == 201
    assert r.json()["alias"] == "ohp"


def test_delete_alias(client, db):
    eid = _seed(db)
    repo = ExerciseRepository(db)
    aid = repo.add_alias(eid, "bench")
    r = client.delete(f"/exercises/aliases/{aid}")
    assert r.status_code == 204
