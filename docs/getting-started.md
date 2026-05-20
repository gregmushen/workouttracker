# Getting Started

## Requirements

- Python 3.12
- SQLite with FTS5 support
- `pip`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For a normal local run, use the packaged CLI:

```bash
workouttracker serve
```

Open the UI at:

```text
http://127.0.0.1:8000
```

## Configure

Set a bearer token and database path:

```bash
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
export WT_DB_PATH="./data/workout.db"
export WT_PUBLIC_BASE_URL="http://localhost:8000"
```

Both are optional for local use. Without flags or environment variables, `workouttracker serve` stores data at `~/.workouttracker/workout.db` and runs without auth. Set `WT_BEARER_TOKEN` or pass `--token` when exposing it beyond your own machine.

## Migrate

```bash
workouttracker migrate
```

## Run

```bash
workouttracker serve
```

Check the API:

```bash
curl -s http://localhost:8000/health
```

## Test

```bash
pytest tests/
ruff check workouttracker scripts tests alembic
```

## Typical Setup Flow

1. Install dependencies.
2. Set `WT_BEARER_TOKEN`.
3. Run `workouttracker migrate`.
4. Import exercise data.
5. Add any personal aliases or preferences.
6. Start logging workout sessions and sets.
