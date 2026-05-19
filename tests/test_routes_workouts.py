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
