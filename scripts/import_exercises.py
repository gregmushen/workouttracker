"""
Bulk import free-exercise-db exercises into the workout tracker database.

Usage:
    python -m scripts.import_exercises <path_to_exercises_json> [db_path]
    python -m scripts.import_exercises <path_to_exercises_json> [db_path] --dry-run
    python -m scripts.import_exercises <path_to_exercises_json> [db_path] \
        --images-root /path/to/free-exercise-db/exercises \
        --public-images-root public/exercise-images

Download from:
    https://github.com/yuhonas/free-exercise-db
    Use: dist/exercises.json
"""
import json
import shutil
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


def _copy_images(image_paths: list[str], images_root: Path, public_images_root: Path) -> int:
    copied = 0
    for rel in image_paths:
        src = images_root / rel
        dest = public_images_root / rel
        if not src.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
    return copied


def import_exercises(file_path: str, db_path: str | None = None,
                     images_root: str | None = None,
                     public_images_root: str = "public/exercise-images",
                     deactivate_missing: bool = False,
                     dry_run: bool = False):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = ExerciseRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        exercises = json.load(f)

    count = 0
    created = 0
    updated = 0
    skipped = 0
    copied_images = 0
    seen_source_codes = []
    image_src_root = Path(images_root) if images_root else None
    image_dest_root = Path(public_images_root)

    for raw in exercises:
        if not raw.get("name"):
            skipped += 1
            continue
        normalized = _normalize_exercise(raw)
        source_code = normalized.pop("source_code")
        seen_source_codes.append(source_code)
        normalized.pop("source", None)
        existing = repo.get_by_source_code("free_exercise_db", source_code)
        if existing:
            updated += 1
        else:
            created += 1
        if not dry_run:
            repo.upsert(source="free_exercise_db", source_code=source_code, **normalized)
            if image_src_root:
                copied_images += _copy_images(raw.get("images", []), image_src_root, image_dest_root)
        count += 1
        if count % 100 == 0:
            print(f"  Imported {count} exercises...", flush=True)

    deactivated = 0
    if deactivate_missing and not dry_run:
        placeholders = ", ".join(["?"] * len(seen_source_codes))
        if seen_source_codes:
            cur = conn.execute(
                f"""UPDATE exercise_templates SET active = 0, updated_at = datetime('now')
                    WHERE source = 'free_exercise_db' AND source_code NOT IN ({placeholders})""",
                seen_source_codes,
            )
            deactivated = cur.rowcount
            conn.commit()

    print(f"Done. Imported {count} exercises.")
    print(f"Created {created}")
    print(f"Updated {updated}")
    print(f"Skipped {skipped}")
    if image_src_root:
        print(f"Copied images {copied_images}")
    if deactivate_missing:
        print(f"Deactivated missing {deactivated}")
    conn.close()


if __name__ == "__main__":
    args = []
    flags = {}
    bool_flags = {"--dry-run", "--deactivate-missing"}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in bool_flags:
            flags[arg.lstrip("-").replace("-", "_")] = True
            i += 1
        elif arg.startswith("--"):
            if i + 1 >= len(sys.argv):
                print(f"Missing value for {arg}")
                sys.exit(1)
            flags[arg.lstrip("-").replace("-", "_")] = sys.argv[i + 1]
            i += 2
        else:
            args.append(arg)
            i += 1

    if not args:
        print("Usage: python -m scripts.import_exercises <path> [db_path] [--dry-run] [--deactivate-missing] [--images-root path] [--public-images-root path]")
        sys.exit(1)
    import_exercises(
        args[0],
        args[1] if len(args) > 1 else None,
        images_root=flags.get("images_root"),
        public_images_root=flags.get("public_images_root", "public/exercise-images"),
        deactivate_missing=flags.get("deactivate_missing", False),
        dry_run=flags.get("dry_run", False),
    )
