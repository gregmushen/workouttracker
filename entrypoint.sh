#!/bin/sh
set -e

DB_PATH="${WT_DB_PATH:-data/workout.db}"
mkdir -p "$(dirname "$DB_PATH")"

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn workouttracker.main:app --host 0.0.0.0 --port 8000
