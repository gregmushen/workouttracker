"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Schema is created by app/database.py init_schema on startup.
    # This migration just marks the initial state as applied.
    # Future migrations must be written as incremental DDL — Alembic does NOT
    # generate DDL from models in this project; database.py is the source of truth.
    pass


def downgrade():
    pass
