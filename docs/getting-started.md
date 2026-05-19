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

## Configure

Set a bearer token and database path:

```bash
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
export WT_DB_PATH="./data/workout.db"
export WT_PUBLIC_BASE_URL="http://localhost:8000"
```

## Migrate

```bash
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

Check the API:

```bash
curl -s http://localhost:8000/health
```

## Test

```bash
pytest tests/
ruff check app scripts tests alembic
```

## Typical Setup Flow

1. Install dependencies.
2. Set `WT_BEARER_TOKEN`.
3. Run migrations.
4. Import exercise data.
5. Add any personal aliases or preferences.
6. Start logging workout sessions and sets.

