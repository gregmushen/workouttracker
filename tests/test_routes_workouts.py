import pytest
from app.repositories.exercises import ExerciseRepository


def _exercise(db, name="Bench Press"):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, equipment="barbell", category="strength")


# --- Sessions ---

def test_create_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"})
    assert r.status_code == 201
    assert r.json()["title"] == "Push"
    assert r.json()["date"] == "2026-05-19"


def test_get_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.get(f"/workouts/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == sid


def test_list_sessions(client, db):
    client.post("/workouts/sessions", json={"date": "2026-05-18", "title": "Pull"})
    client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"})
    r = client.get("/workouts/sessions?start=2026-05-18&end=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_close_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.post(f"/workouts/sessions/{sid}/close", json={"notes": "great session"})
    assert r2.status_code == 200
    assert r2.json()["ended_at"] is not None
    assert r2.json()["notes"] == "great session"


def test_update_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.patch(f"/workouts/sessions/{sid}", json={"title": "Legs", "energy_score": 8})
    assert r2.status_code == 200
    assert r2.json()["title"] == "Legs"
    assert r2.json()["energy_score"] == 8


def test_delete_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.delete(f"/workouts/sessions/{sid}")
    assert r2.status_code == 204


def _session(client):
    return client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"}).json()["id"]


def test_create_set(client, db):
    eid = _exercise(db)
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid,
        "weight": 135,
        "weight_unit": "lb",
        "reps": 8,
        "set_type": "working",
    })
    assert r.status_code == 201
    assert r.json()["weight"] == 135
    assert r.json()["reps"] == 8


def test_bulk_create_sets(client, db):
    eid = _exercise(db, "Barbell Bench Press")
    ExerciseRepository(db).add_alias(eid, "bench")
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets/bulk", json={
        "exercise_query": "bench",
        "sets": [
            {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
            {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
            {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"},
        ],
    })
    assert r.status_code == 201
    assert len(r.json()) == 3
    assert r.json()[0]["weight"] == 135


def test_bulk_sets_unknown_exercise(client, db):
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets/bulk", json={
        "exercise_query": "xyzzy_unknown",
        "sets": [{"weight": 100, "weight_unit": "lb", "reps": 5}],
    })
    assert r.status_code == 404


def test_recent(client, db):
    eid = _exercise(db)
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "weight": 135,
        "weight_unit": "lb", "reps": 8, "set_type": "working",
    })
    r = client.get(f"/workouts/recent?exercise_id={eid}")
    assert r.status_code == 200


def test_personal_records(client, db):
    eid = _exercise(db)
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "weight": 225,
        "weight_unit": "lb", "reps": 5, "set_type": "working",
    })
    r = client.get("/workouts/personal-records")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_summary(client, db):
    r = client.get("/workouts/summary")
    assert r.status_code == 200
    assert "sessions" in r.json()
