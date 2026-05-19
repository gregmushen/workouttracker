from app.repositories.exercises import ExerciseRepository


def _repo(db):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo


def test_create_and_get(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Barbell Bench Press",
                      equipment="barbell", category="strength",
                      primary_muscles='["chest","triceps"]')
    ex = repo.get(eid)
    assert ex["name"] == "Barbell Bench Press"
    assert ex["equipment"] == "barbell"


def test_search_fts_by_name(db):
    repo = _repo(db)
    repo.create(source="custom", name="Barbell Squat", equipment="barbell", category="strength")
    repo.create(source="custom", name="Leg Press", equipment="machine", category="strength")
    results = repo.search_fts("squat")
    assert len(results) == 1
    assert results[0]["name"] == "Barbell Squat"


def test_upsert_by_source_code(db):
    repo = _repo(db)
    repo.upsert(source="free_exercise_db", source_code="bench_press",
                name="Bench Press", equipment="barbell", category="strength")
    repo.upsert(source="free_exercise_db", source_code="bench_press",
                name="Bench Press (updated)", equipment="barbell", category="strength")
    results = repo.search_fts("bench")
    assert len(results) == 1
    assert results[0]["name"] == "Bench Press (updated)"


def test_add_and_get_alias(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Barbell Bench Press",
                      equipment="barbell", category="strength")
    repo.add_alias(eid, "bench")
    result = repo.get_by_alias("bench")
    assert result["id"] == eid


def test_delete_alias(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Squat", equipment="barbell", category="strength")
    alias_id = repo.add_alias(eid, "sq")
    repo.delete_alias(alias_id)
    assert repo.get_by_alias("sq") is None


def test_list_aliases(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Deadlift", equipment="barbell", category="strength")
    repo.add_alias(eid, "dl")
    repo.add_alias(eid, "deadlift")
    aliases = repo.list_aliases(eid)
    assert len(aliases) == 2
