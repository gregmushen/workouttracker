from workouttracker.repositories.exercises import ExerciseRepository


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


# --- Cardio metrics ---

CARDIO_METRICS = {
    "avg_watts": 60,
    "avg_heart_rate_bpm": 120,
    "max_heart_rate_bpm": 135,
    "calories_kcal": 225,
    "avg_cadence_rpm": 82,
}


def test_create_set_with_cardio_metrics(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid,
        "set_type": "timed",
        "duration_seconds": 3600,
        "notes": "easy zone 2",
        **CARDIO_METRICS,
    })
    assert r.status_code == 201
    body = r.json()
    for field, value in CARDIO_METRICS.items():
        assert body[field] == value


def test_create_set_without_cardio_metrics_returns_nulls(client, db):
    eid = _exercise(db)
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "weight": 135,
        "weight_unit": "lb", "reps": 8, "set_type": "working",
    })
    assert r.status_code == 201
    for field in CARDIO_METRICS:
        assert r.json()[field] is None


def test_update_set_with_cardio_metrics(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    sid = _session(client)
    set_id = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "set_type": "timed", "duration_seconds": 1800,
    }).json()["id"]
    r = client.patch(f"/workouts/sets/{set_id}", json=CARDIO_METRICS)
    assert r.status_code == 200
    for field, value in CARDIO_METRICS.items():
        assert r.json()[field] == value


def test_update_set_clears_cardio_metric(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    sid = _session(client)
    set_id = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "set_type": "timed",
        "duration_seconds": 1800, "avg_watts": 60,
    }).json()["id"]
    r = client.patch(f"/workouts/sets/{set_id}", json={"avg_watts": None})
    assert r.status_code == 200
    assert r.json()["avg_watts"] is None


def test_bulk_create_sets_with_cardio_metrics(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    ExerciseRepository(db).add_alias(eid, "stationary bike")
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets/bulk", json={
        "exercise_query": "stationary bike",
        "sets": [
            {"set_type": "timed", "duration_seconds": 1800, **CARDIO_METRICS},
            {"set_type": "timed", "duration_seconds": 900, "avg_watts": 90},
        ],
    })
    assert r.status_code == 201
    assert r.json()[0]["avg_heart_rate_bpm"] == 120
    assert r.json()[1]["avg_watts"] == 90
    assert r.json()[1]["avg_heart_rate_bpm"] is None


def test_list_sets_includes_cardio_metrics(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "set_type": "timed",
        "duration_seconds": 3600, **CARDIO_METRICS,
    })
    r = client.get(f"/workouts/sessions/{sid}/sets")
    assert r.status_code == 200
    assert r.json()[0]["avg_watts"] == 60


def test_recent_includes_cardio_metrics(client, db):
    eid = _exercise(db, "Bicycling, Stationary")
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "set_type": "timed",
        "duration_seconds": 3600, **CARDIO_METRICS,
    })
    r = client.get(f"/workouts/recent?exercise_id={eid}")
    assert r.status_code == 200
    assert r.json()["sessions"][0]["sets"][0]["calories_kcal"] == 225


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
