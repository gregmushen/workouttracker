from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService


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
