"""cardio set metrics

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

COLUMNS = [
    ("avg_watts", "REAL"),
    ("avg_heart_rate_bpm", "INTEGER"),
    ("max_heart_rate_bpm", "INTEGER"),
    ("calories_kcal", "REAL"),
    ("avg_cadence_rpm", "REAL"),
]


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").mappings().all()
    return column in {row["name"] for row in rows}


def upgrade():
    for column, coltype in COLUMNS:
        if not _has_column("workout_sets", column):
            op.execute(f"ALTER TABLE workout_sets ADD COLUMN {column} {coltype}")


def downgrade():
    for column, _ in reversed(COLUMNS):
        if _has_column("workout_sets", column):
            op.execute(f"ALTER TABLE workout_sets DROP COLUMN {column}")
