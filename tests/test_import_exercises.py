import json
import os
import tempfile
from pathlib import Path
from scripts.import_exercises import import_exercises
from workouttracker.database import get_connection
from workouttracker.repositories.exercises import ExerciseRepository

SAMPLE = [
    {
        "id": "Barbell_Bench_Press_-_Medium_Grip",
        "name": "Barbell Bench Press - Medium Grip",
        "force": "push",
        "level": "beginner",
        "mechanic": "compound",
        "equipment": "barbell",
        "primaryMuscles": ["chest"],
        "secondaryMuscles": ["shoulders", "triceps"],
        "instructions": ["Lie on bench", "Lower bar to chest"],
        "category": "strength",
        "images": [],
    },
    {
        "id": "Squat",
        "name": "Barbell Squat",
        "force": "push",
        "level": "intermediate",
        "mechanic": "compound",
        "equipment": "barbell",
        "primaryMuscles": ["quadriceps"],
        "secondaryMuscles": ["glutes"],
        "instructions": ["Stand with bar on upper back"],
        "category": "strength",
        "images": [],
    },
]


def test_import_creates_exercises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE, f)
        path = f.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as dbf:
        db_path = dbf.name
    try:
        import_exercises(path, db_path)
        import pathlib
        conn = get_connection(pathlib.Path(db_path))
        repo = ExerciseRepository(conn)
        repo.ensure_fts()
        results = repo.search_fts("bench")
        assert len(results) == 1
        assert results[0]["equipment"] == "barbell"
        assert results[0]["source"] == "free_exercise_db"
        conn.close()
    finally:
        os.unlink(path)
        os.unlink(db_path)


def test_import_is_idempotent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE, f)
        path = f.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as dbf:
        db_path = dbf.name
    try:
        import_exercises(path, db_path)
        import_exercises(path, db_path)
        import pathlib
        conn = get_connection(pathlib.Path(db_path))
        total = conn.execute(
            "SELECT COUNT(*) FROM exercise_templates WHERE source='free_exercise_db'"
        ).fetchone()[0]
        assert total == 2
        conn.close()
    finally:
        os.unlink(path)
        os.unlink(db_path)


def test_import_copies_images():
    sample = [{**SAMPLE[0], "images": ["Bench/0.jpg"]}]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        json_path = root / "exercises.json"
        db_path = root / "workout.db"
        images_root = root / "source-images"
        public_root = root / "public" / "exercise-images"
        (images_root / "Bench").mkdir(parents=True)
        (images_root / "Bench" / "0.jpg").write_bytes(b"fake image")
        json_path.write_text(json.dumps(sample))

        import_exercises(
            str(json_path),
            str(db_path),
            images_root=str(images_root),
            public_images_root=str(public_root),
        )

        assert (public_root / "Bench" / "0.jpg").read_bytes() == b"fake image"


def test_import_dry_run_does_not_write():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE, f)
        path = f.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as dbf:
        db_path = dbf.name
    try:
        import_exercises(path, db_path, dry_run=True)
        conn = get_connection(Path(db_path))
        total = conn.execute(
            "SELECT COUNT(*) FROM exercise_templates WHERE source='free_exercise_db'"
        ).fetchone()[0]
        assert total == 0
        conn.close()
    finally:
        os.unlink(path)
        os.unlink(db_path)
