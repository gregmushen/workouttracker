from __future__ import annotations

import argparse
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


DEFAULT_DATA_DIR = Path.home() / ".workouttracker"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "workout.db"


def _set_db_env(db_path: str | None) -> Path:
    path = Path(db_path).expanduser() if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["WT_DB_PATH"] = str(path)
    return path


def _run_schema_setup(db_path: Path) -> None:
    from app.database import get_connection, init_schema
    from app.repositories.exercises import ExerciseRepository

    conn = get_connection(db_path)
    try:
        init_schema(conn)
        ExerciseRepository(conn).ensure_fts()
    finally:
        conn.close()


def _cmd_serve(args: argparse.Namespace) -> int:
    db_path = _set_db_env(args.db)
    if args.token:
        os.environ["WT_BEARER_TOKEN"] = args.token
    _run_schema_setup(db_path)

    print(f"Workout Tracker serving at http://{args.host}:{args.port}")
    print(f"Database: {db_path}")
    print(f"OpenAPI: http://{args.host}:{args.port}/openapi.json")

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    db_path = _set_db_env(args.db)
    _run_schema_setup(db_path)
    print(f"Schema ready: {db_path}")
    return 0


def _cmd_import_exercises(args: argparse.Namespace) -> int:
    db_path = _set_db_env(args.db)
    _run_schema_setup(db_path)

    from scripts.import_exercises import import_exercises

    import_exercises(
        args.file,
        str(db_path),
        images_root=args.images_root,
        public_images_root=args.public_images_root,
        deactivate_missing=args.deactivate_missing,
        dry_run=args.dry_run,
    )
    return 0


def _cmd_version(_: argparse.Namespace) -> int:
    try:
        print(version("workouttracker"))
    except PackageNotFoundError:
        from app.config import settings

        print(settings.api_version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workouttracker")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the Workout Tracker API and web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--db", default=None, help="SQLite database path")
    serve.add_argument("--token", default=None, help="Bearer token required by the API")
    serve.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    serve.set_defaults(func=_cmd_serve)

    migrate = sub.add_parser("migrate", help="Create or update the local database schema")
    migrate.add_argument("--db", default=None, help="SQLite database path")
    migrate.set_defaults(func=_cmd_migrate)

    imp = sub.add_parser("import-exercises", help="Import free-exercise-db exercises")
    imp.add_argument("file", help="Path to free-exercise-db dist/exercises.json")
    imp.add_argument("--db", default=None, help="SQLite database path")
    imp.add_argument("--images-root", default=None, help="Path to free-exercise-db exercises image directory")
    imp.add_argument("--public-images-root", default="public/exercise-images")
    imp.add_argument("--deactivate-missing", action="store_true")
    imp.add_argument("--dry-run", action="store_true")
    imp.set_defaults(func=_cmd_import_exercises)

    ver = sub.add_parser("version", help="Print package version")
    ver.set_defaults(func=_cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
