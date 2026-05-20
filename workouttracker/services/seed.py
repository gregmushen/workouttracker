from __future__ import annotations

import json
from importlib import resources
from sqlite3 import Connection

from workouttracker.repositories.exercises import ExerciseRepository


def _normalize_exercise(raw: dict) -> dict:
    return {
        "source": "free_exercise_db",
        "source_code": raw.get("id", ""),
        "name": raw.get("name", ""),
        "category": raw.get("category") or None,
        "equipment": raw.get("equipment") or None,
        "force": raw.get("force") or None,
        "level": raw.get("level") or None,
        "mechanic": raw.get("mechanic") or None,
        "primary_muscles": json.dumps(raw.get("primaryMuscles", [])),
        "secondary_muscles": json.dumps(raw.get("secondaryMuscles", [])),
        "instructions": json.dumps(raw.get("instructions", [])),
        "image_paths": json.dumps(raw.get("images", [])),
    }


def import_free_exercise_db(conn: Connection, exercises: list[dict]) -> int:
    repo = ExerciseRepository(conn)
    repo.ensure_fts()
    count = 0
    for raw in exercises:
        if not raw.get("name"):
            continue
        normalized = _normalize_exercise(raw)
        source_code = normalized.pop("source_code")
        normalized.pop("source", None)
        repo.upsert(source="free_exercise_db", source_code=source_code, **normalized)
        count += 1
    return count


def load_packaged_exercises() -> list[dict]:
    resource = resources.files("workouttracker.seed.free_exercise_db").joinpath("exercises.json")
    return json.loads(resource.read_text())


def seed_default_exercises(conn: Connection) -> int:
    repo = ExerciseRepository(conn)
    repo.ensure_fts()
    if repo.count() > 0:
        return 0
    return import_free_exercise_db(conn, load_packaged_exercises())
