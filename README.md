# Workout Tracker

A personal lifting and workout tracking API built with FastAPI and SQLite.

**Live:** https://wt.paracosmlab.com — OpenAPI schema at `/openapi.json`

## What it does

REST API for logging strength training sessions, sets, and tracking progress.

Key endpoints:
- `GET /exercises/search?q=` — full-text search with alias support (e.g. "bench" → Barbell Bench Press)
- `POST /workouts/sessions` — start a workout session
- `POST /workouts/sessions/{id}/sets/bulk` — log multiple sets in one call
- `GET /workouts/recent?exercise_id=` — last N sessions for an exercise
- `GET /workouts/progress?exercise_id=` — e1RM trend and volume over time
- `GET /workouts/personal-records` — best estimated 1RM per exercise
- `POST /workouts/sessions/{id}/close` — close out a session

All endpoints require `Authorization: Bearer <token>`.

## Stack

Python 3.12, FastAPI, SQLite (WAL + FTS5), Kamal 2, Woodpecker CI, Cloudflare tunnel.

## Local development

```bash
pip install -e ".[dev]"
pytest tests/
```

## Exercise data import

Download [free-exercise-db](https://github.com/yuhonas/free-exercise-db):

```bash
# On garageband:
wget -O /home/gregmushen/workout-data/exercises.json \
  "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"

bin/import-exercises /home/gregmushen/workout-data/exercises.json
```

Re-running is safe — exercises are upserted by `(source, source_code)`.

## Bulk set logging

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "bench",
    "sets": [
      {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
      {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
      {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"}
    ]
  }' \
  "https://wt.paracosmlab.com/workouts/sessions/1/sets/bulk"
```

## License

MIT.

