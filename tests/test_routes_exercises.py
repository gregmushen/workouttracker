from app.repositories.exercises import ExerciseRepository


def _seed(db, name="Bench Press", **kwargs):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    kwargs.setdefault("equipment", "barbell")
    kwargs.setdefault("category", "strength")
    return repo.create(source="custom", name=name, **kwargs)


def test_search_exercises(client, db):
    _seed(db, "Barbell Squat")
    _seed(db, "Leg Press")
    r = client.get("/exercises/search?q=squat")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Barbell Squat"


def test_search_filters_and_image_urls(client, db):
    _seed(db, "Dumbbell Bench Press", equipment="dumbbell",
          primary_muscles='["chest"]', image_paths='["Dumbbell_Bench_Press/0.jpg"]')
    _seed(db, "Barbell Bench Press", equipment="barbell",
          primary_muscles='["chest"]')
    r = client.get("/exercises/search?q=bench&equipment=dumbbell&muscle=chest")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Dumbbell Bench Press"
    assert data[0]["image_urls"][0].endswith("/exercise-images/Dumbbell_Bench_Press/0.jpg")


def test_get_exercise(client, db):
    eid = _seed(db)
    r = client.get(f"/exercises/{eid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Bench Press"
    assert "image_urls" in r.json()


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
    assert client.get(f"/exercises/{eid}").status_code == 404


def test_add_alias(client, db):
    eid = _seed(db, "Overhead Press")
    r = client.post(f"/exercises/{eid}/aliases", json={"alias": "ohp"})
    assert r.status_code == 201
    assert r.json()["alias"] == "ohp"
    assert r.json()["source"] == "user"


def test_list_aliases(client, db):
    eid = _seed(db, "Overhead Press")
    client.post(f"/exercises/{eid}/aliases", json={"alias": "ohp", "source": "agent"})
    r = client.get(f"/exercises/{eid}/aliases")
    assert r.status_code == 200
    assert r.json()[0]["alias"] == "ohp"
    assert r.json()[0]["source"] == "agent"


def test_delete_alias(client, db):
    eid = _seed(db)
    repo = ExerciseRepository(db)
    aid = repo.add_alias(eid, "bench")
    r = client.delete(f"/exercises/aliases/{aid}")
    assert r.status_code == 204


def test_resolve_exact_alias(client, db):
    eid = _seed(db, "Barbell Bench Press")
    ExerciseRepository(db).add_alias(eid, "bench")
    r = client.post("/exercises/resolve", json={"query": "bench"})
    assert r.status_code == 200
    data = r.json()
    assert data["best_match"]["id"] == eid
    assert data["needs_confirmation"] is False


def test_resolve_ambiguous_query_requires_confirmation(client, db):
    _seed(db, "Bent Over Barbell Row")
    _seed(db, "One-Arm Dumbbell Row")
    r = client.post("/exercises/resolve", json={"query": "row"})
    assert r.status_code == 200
    data = r.json()
    assert data["needs_confirmation"] is True
    assert len(data["alternatives"]) >= 2


def test_preferences_affect_resolution(client, db):
    eid = _seed(db, "One-Arm Dumbbell Row")
    r = client.post("/exercises/preferences", json={
        "phrase": "row",
        "preferred_exercise_id": eid,
        "context": {"equipment": "dumbbell"},
    })
    assert r.status_code == 201
    assert r.json()["context"]["equipment"] == "dumbbell"

    resolved = client.post("/exercises/resolve", json={"query": "row"})
    assert resolved.status_code == 200
    assert resolved.json()["best_match"]["id"] == eid
    assert resolved.json()["needs_confirmation"] is False

    prefs = client.get("/exercises/preferences")
    assert prefs.status_code == 200
    assert len(prefs.json()) == 1


def test_facets(client, db):
    _seed(db, "Barbell Squat", equipment="barbell", category="strength",
          level="beginner", mechanic="compound", force="push",
          primary_muscles='["quadriceps"]')
    r = client.get("/exercises/facets")
    assert r.status_code == 200
    data = r.json()
    assert "barbell" in data["equipment"]
    assert "quadriceps" in data["muscles"]
