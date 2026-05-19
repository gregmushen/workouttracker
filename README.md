# Workout Tracker

A personal lifting and workout tracking API built with FastAPI and SQLite.

Workout Tracker provides a structured backend for logging strength training sessions, searching exercises, resolving shorthand exercise names, and tracking progress over time. It is designed to work well with CLI tools and AI agents.

## Features

- Bearer-token protected FastAPI API
- SQLite database with WAL mode, FTS5 search, and Alembic migrations
- Exercise library import from `free-exercise-db`
- Full-text exercise search with alias and filter support
- Exercise resolution endpoint for AI/agent workflows
- Exercise preferences for remembering user-specific phrase mappings
- Exercise aliases for shorthand such as `bench`, `ohp`, or `db row`
- Static exercise image support under `/exercise-images/...`
- Workout sessions
- Workout sets with reps, weight, RPE, RIR, rest, duration, and distance fields
- Bulk set logging by exercise query
- Recent history, progress, personal record, and summary endpoints

## API

All endpoints except `/health` require:

```http
Authorization: Bearer <token>
```

Key endpoints:

```http
GET  /health
GET  /openapi.json
GET  /exercises/search?q=bench&limit=10
POST /exercises/resolve
GET  /exercises/facets
GET  /exercises/preferences
POST /exercises/preferences
GET  /exercises/{id}
POST /exercises
PATCH /exercises/{id}
DELETE /exercises/{id}
GET  /exercises/{id}/aliases
POST /exercises/{id}/aliases
POST /workouts/sessions
GET  /workouts/sessions
POST /workouts/sessions/{id}/sets
POST /workouts/sessions/{id}/sets/bulk
GET  /workouts/recent?exercise_id=123
GET  /workouts/progress?exercise_id=123
GET  /workouts/personal-records
GET  /workouts/summary
POST /workouts/sessions/{id}/close
```

## Stack

- Python 3.12
- FastAPI
- SQLite
- Alembic
- Pytest
- Ruff
- Docker/Kamal-compatible deployment

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
ruff check app scripts tests alembic
uvicorn app.main:app --reload
```

Useful environment variables:

```bash
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
export WT_DB_PATH="./data/workout.db"
export WT_PUBLIC_BASE_URL="http://localhost:8000"
```

Run migrations:

```bash
alembic upgrade head
```

## Exercise Data

This project uses [free-exercise-db](https://github.com/yuhonas/free-exercise-db) as the seed exercise dataset.

Credit:

- Project: `free-exercise-db`
- Repository: https://github.com/yuhonas/free-exercise-db
- License: Unlicense / public domain
- Data used: exercise names, categories, equipment, force, level, mechanic, primary/secondary muscles, instructions, and image paths

Download the exercise JSON:

```bash
curl -L \
  -o data/exercises.json \
  "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
```

Import exercises:

```bash
python -m scripts.import_exercises data/exercises.json ./data/workout.db
```

Import exercises and copy images from a local clone of `free-exercise-db`:

```bash
python -m scripts.import_exercises \
  /path/to/free-exercise-db/dist/exercises.json \
  ./data/workout.db \
  --images-root /path/to/free-exercise-db/exercises \
  --public-images-root public/exercise-images
```

Useful import flags:

- `--dry-run` validates and reports without writing
- `--deactivate-missing` marks imported exercises inactive if missing from the new source file

Re-running the import is safe. Exercises are upserted by `(source, source_code)`.

## Static Images

Exercise images should be served from public static files:

```text
public/
  exercise-images/
    3_4_Sit-Up/
      0.jpg
      1.jpg
```

The database stores relative paths such as:

```json
["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"]
```

API responses resolve those paths into `image_urls` using `WT_PUBLIC_BASE_URL` or the request base URL.

## Exercise Resolution

`POST /exercises/resolve` converts fuzzy user language into a canonical exercise ID.

Example request:

```json
{
  "query": "bench",
  "context": {
    "equipment_available": ["barbell", "dumbbell"],
    "recent_exercise_ids": [],
    "session_title": "Upper",
    "goal": "strength"
  }
}
```

The response includes:

- `best_match`
- `alternatives`
- `confidence`
- `match_reason`
- `needs_confirmation`
- `confirmation_prompt`

## Bulk Set Logging

```bash
curl -s -X POST \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "bench",
    "sets": [
      {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
      {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
      {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"}
    ]
  }' \
  "$WT_BASE_URL/workouts/sessions/1/sets/bulk"
```

## Specs

- [Lifting Tracker API](docs/superpowers/specs/2026-05-19-lifting-tracker-design.md)
- [Exercise Library API](docs/superpowers/specs/2026-05-19-exercise-library-api.md)

## License

MIT. See [LICENSE](LICENSE).

