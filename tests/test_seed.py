import sqlite3

from workouttracker.database import init_schema
from workouttracker.repositories.exercises import ExerciseRepository
from workouttracker.services.seed import load_packaged_exercises, seed_default_exercises


def test_packaged_seed_loads_exercises():
    exercises = load_packaged_exercises()
    assert len(exercises) > 800
    assert {"id", "name", "primaryMuscles"}.issubset(exercises[0])


def test_seed_default_exercises_only_when_empty():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    repo = ExerciseRepository(conn)
    repo.ensure_fts()

    first = seed_default_exercises(conn)
    second = seed_default_exercises(conn)

    assert first > 800
    assert second == 0
    assert repo.count() == first
    assert repo.search_fts("bench")
    conn.close()
