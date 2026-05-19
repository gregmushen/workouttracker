import sqlite3
from pathlib import Path
from app.config import settings


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercise_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'custom'
                CHECK(source IN ('free_exercise_db', 'custom')),
            source_code TEXT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL DEFAULT '',
            category TEXT,
            equipment TEXT,
            force TEXT,
            level TEXT,
            mechanic TEXT,
            primary_muscles TEXT NOT NULL DEFAULT '[]',
            secondary_muscles TEXT NOT NULL DEFAULT '[]',
            instructions TEXT NOT NULL DEFAULT '[]',
            image_paths TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS exercise_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_template_id INTEGER NOT NULL
                REFERENCES exercise_templates(id) ON DELETE CASCADE,
            alias TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(alias)
        );

        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            title TEXT,
            location TEXT,
            body_weight_kg REAL,
            energy_score INTEGER,
            soreness_score INTEGER,
            stress_score INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL
                REFERENCES workout_sessions(id) ON DELETE CASCADE,
            exercise_template_id INTEGER NOT NULL
                REFERENCES exercise_templates(id),
            set_number INTEGER NOT NULL DEFAULT 1,
            set_type TEXT NOT NULL DEFAULT 'working'
                CHECK(set_type IN ('warmup','working','drop','failure','amrap','bodyweight','timed')),
            weight REAL,
            weight_unit TEXT CHECK(weight_unit IN ('lb','kg')),
            reps REAL,
            duration_seconds INTEGER,
            distance REAL,
            distance_unit TEXT CHECK(distance_unit IN ('m','ft','mi')),
            rpe REAL,
            rir REAL,
            rest_seconds INTEGER,
            notes TEXT,
            performed_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_source_code
            ON exercise_templates(source, source_code) WHERE source_code IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_exercise_name
            ON exercise_templates(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_date
            ON workout_sessions(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_sets_session
            ON workout_sets(session_id);
        CREATE INDEX IF NOT EXISTS idx_sets_exercise
            ON workout_sets(exercise_template_id);
    """)
