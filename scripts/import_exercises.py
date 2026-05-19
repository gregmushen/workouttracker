"""
Bulk import free-exercise-db exercises into the workout tracker database.

Usage:
    python -m scripts.import_exercises <path_to_exercises_json> [db_path]

Download from:
    https://github.com/yuhonas/free-exercise-db
    Use: dist/exercises.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.exercises import ExerciseRepository


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


def import_exercises(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = ExerciseRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        exercises = json.load(f)

    count = 0
    for raw in exercises:
        if not raw.get("name"):
            continue
        normalized = _normalize_exercise(raw)
        source_code = normalized.pop("source_code")
        normalized.pop("source", None)
        repo.upsert(source="free_exercise_db", source_code=source_code, **normalized)
        count += 1
        if count % 100 == 0:
            print(f"  Imported {count} exercises...", flush=True)

    print(f"Done. Imported {count} exercises.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_exercises <path> [db_path]")
        sys.exit(1)
    import_exercises(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
