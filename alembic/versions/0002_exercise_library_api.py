"""exercise library api

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-19
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").mappings().all()
    return column in {row["name"] for row in rows}


def upgrade():
    if not _has_column("exercise_templates", "active"):
        op.execute("ALTER TABLE exercise_templates ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

    if not _has_column("exercise_aliases", "normalized_alias"):
        op.execute("ALTER TABLE exercise_aliases ADD COLUMN normalized_alias TEXT NOT NULL DEFAULT ''")
    if not _has_column("exercise_aliases", "source"):
        op.execute("ALTER TABLE exercise_aliases ADD COLUMN source TEXT NOT NULL DEFAULT 'user'")
    if not _has_column("exercise_aliases", "confidence"):
        op.execute("ALTER TABLE exercise_aliases ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0")

    op.execute(
        "UPDATE exercise_aliases SET normalized_alias = lower(trim(alias)) WHERE normalized_alias = ''"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS exercise_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            phrase TEXT NOT NULL,
            normalized_phrase TEXT NOT NULL,
            preferred_exercise_id INTEGER NOT NULL
                REFERENCES exercise_templates(id) ON DELETE CASCADE,
            context TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, normalized_phrase)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS exercise_search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            query TEXT NOT NULL,
            matched_exercise_id INTEGER REFERENCES exercise_templates(id),
            confidence REAL,
            required_confirmation INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_exercise_category ON exercise_templates(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_exercise_equipment ON exercise_templates(equipment)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_alias_normalized ON exercise_aliases(normalized_alias)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_alias_normalized")
    op.execute("DROP INDEX IF EXISTS idx_exercise_equipment")
    op.execute("DROP INDEX IF EXISTS idx_exercise_category")
    op.execute("DROP TABLE IF EXISTS exercise_search_logs")
    op.execute("DROP TABLE IF EXISTS exercise_preferences")

    # SQLite cannot drop columns without table rebuilds. Leave additive columns
    # in place on downgrade; they are harmless and preserve data.

