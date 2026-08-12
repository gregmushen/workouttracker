from workouttracker.repositories.exercises import ExerciseRepository
from workouttracker.services.exercise_search import ExerciseSearchService


def _seed(db, name, **kwargs):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, **kwargs)


def test_search_falls_back_to_fts(db):
    eid = _seed(db, "Barbell Bench Press", equipment="barbell")
    svc = ExerciseSearchService(ExerciseRepository(db))
    results = svc.search("bench")
    assert len(results) >= 1
    assert any(r["id"] == eid for r in results)


def test_alias_takes_priority(db):
    eid1 = _seed(db, "Barbell Bench Press", equipment="barbell")
    _seed(db, "Bench Something Else", equipment="dumbbell")
    repo = ExerciseRepository(db)
    repo.add_alias(eid1, "bench")
    svc = ExerciseSearchService(repo)
    results = svc.search("bench")
    assert results[0]["id"] == eid1


def test_resolve_returns_single(db):
    eid = _seed(db, "Overhead Press", equipment="barbell")
    repo = ExerciseRepository(db)
    repo.add_alias(eid, "ohp")
    svc = ExerciseSearchService(repo)
    ex = svc.resolve("ohp")
    assert ex["id"] == eid


def test_resolve_returns_none_for_unknown(db):
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert svc.resolve("xyzzy") is None


# --- Punctuated names ---
# An unescaped comma makes the generated FTS5 MATCH expression a syntax error,
# which search_fts swallows into an empty list. Names carrying punctuation are
# common in the cardio library ("Bicycling, Stationary").

def test_search_finds_name_containing_a_comma(db):
    eid = _seed(db, "Bicycling, Stationary", equipment="machine", category="cardio")
    svc = ExerciseSearchService(ExerciseRepository(db))
    results = svc.search("Bicycling, Stationary")
    assert any(r["id"] == eid for r in results)


def test_resolve_finds_name_containing_a_comma(db):
    eid = _seed(db, "Bicycling, Stationary", equipment="machine", category="cardio")
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert svc.resolve("Bicycling, Stationary")["id"] == eid


def test_search_finds_name_containing_an_apostrophe(db):
    eid = _seed(db, "Farmer's Walk", equipment="dumbbell")
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert any(r["id"] == eid for r in svc.search("Farmer's Walk"))


def test_search_survives_punctuation_only_query(db):
    _seed(db, "Bench Press")
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert svc.search(",,,") == []


def test_exact_name_resolves_over_fuzzy_neighbours(db):
    _seed(db, "Bicycling, Mountain", category="cardio")
    exact = _seed(db, "Bicycling, Stationary", category="cardio")
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert svc.resolve("Bicycling, Stationary")["id"] == exact
