# Workout Tracker

A personal workout and lifting tracker API built with FastAPI and SQLite.

**Live:** https://wt.paracosmlab.com  
**OpenAPI:** https://wt.paracosmlab.com/openapi.json

## What It Does

Workout Tracker is a structured backend for logging lifting sessions, searching exercises, and giving AI agents a reliable system of record.

It is designed for workflows like:

```text
bench 135x8, 155x5, 165x3
what did I squat last time?
show my recent push workouts
close out this workout
```

The app intentionally keeps the API explicit and boring. Natural language parsing, coaching, reminders, and daily review can live in Hermes or another agent on top of the API.

## Current Features

- Bearer-token protected FastAPI service
- SQLite storage with app-managed schema initialization
- Exercise library seeded from `free-exercise-db`
- FTS5 exercise search across names, equipment, categories, and muscles
- Exercise aliases for shorthand like `bench`, `ohp`, or `db row`
- Custom exercise CRUD
- Workout sessions
- Workout sets with reps, weight, RPE, RIR, rest, duration, and distance fields
- Bulk set logging by exercise query
- Recent/progress endpoint stubs
- Production import helper for exercise data

## Data Source

The exercise library is seeded from:

```text
https://github.com/yuhonas/free-exercise-db
```

That dataset is public-domain/Unlicense and includes 873 exercises with:

- name
- category
- equipment
- force
- level
- mechanic
- primary/secondary muscles
- instructions
- image paths

The project also references wger as a domain-model inspiration source, but does not copy wger code because wger is AGPL-3.0.

## API

All endpoints except `/health` require:

```http
Authorization: Bearer <token>
```

### Health

```http
GET /health
```

### Exercises

```http
GET /exercises/search?q=bench&limit=10
GET /exercises/{exercise_id}
POST /exercises
PATCH /exercises/{exercise_id}
DELETE /exercises/{exercise_id}
POST /exercises/{exercise_id}/aliases
DELETE /exercises/aliases/{alias_id}
```

Example search:

```bash
curl -s "https://wt.paracosmlab.com/exercises/search?q=bench&limit=5" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

### Workout Sessions

```http
POST /workouts/sessions
GET /workouts/sessions
GET /workouts/sessions/{session_id}
PATCH /workouts/sessions/{session_id}
POST /workouts/sessions/{session_id}/close
DELETE /workouts/sessions/{session_id}
```

Create a session:

```json
{
  "date": "2026-05-19",
  "title": "Upper",
  "location": "garage",
  "energy_score": 7,
  "soreness_score": 3,
  "stress_score": 4,
  "notes": "First session back."
}
```

### Workout Sets

```http
POST /workouts/sessions/{session_id}/sets
POST /workouts/sessions/{session_id}/sets/bulk
PATCH /workouts/sets/{set_id}
DELETE /workouts/sets/{set_id}
```

Create one set:

```json
{
  "exercise_template_id": 123,
  "set_number": 1,
  "set_type": "working",
  "weight": 135,
  "weight_unit": "lb",
  "reps": 8,
  "rpe": 7.5,
  "rir": 2
}
```

Bulk log sets by exercise query:

```json
{
  "exercise_query": "bench",
  "sets": [
    {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
    {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
    {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"}
  ]
}
```

### History And Progress

```http
GET /workouts/recent?exercise_id=123&limit=5
GET /workouts/progress?exercise_id=123&start=2026-01-01&end=2026-05-19
GET /workouts/personal-records
GET /workouts/summary?start=2026-05-01&end=2026-05-19
```

These endpoints exist, but the richer progress formatting is still being built.

## Local Development

```bash
cd ~/work/code/workouttracker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
uvicorn app.main:app --reload
```

Useful environment variables:

```bash
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
export WT_DB_PATH="./data/workout.db"
```

## Import Exercises

Clone or download `free-exercise-db`, then import its bundled JSON:

```bash
python -m scripts.import_exercises /path/to/free-exercise-db/dist/exercises.json ./data/workout.db
```

For production on `garageband`, copy the JSON to the host and run:

```bash
bin/import-exercises /home/gregmushen/workout-data/exercises.json
```

The import upserts by `(source, source_code)` and preserves existing aliases.

## Static Exercise Images

The specs expect exercise images to be served as public static files:

```text
public/
  exercise-images/
    3_4_Sit-Up/
      0.jpg
      1.jpg
```

The database should store relative paths like:

```json
["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"]
```

Future API responses should resolve those to public URLs like:

```text
https://wt.paracosmlab.com/exercise-images/3_4_Sit-Up/0.jpg
```

Image serving and resolved `image_urls` are part of the exercise library roadmap.

## Agent Workflow

The intended Hermes flow is:

1. Search or resolve an exercise phrase.
2. Create or find today's workout session.
3. Log one or more sets.
4. Close the workout with notes and recovery scores.
5. Review recent performance and suggest conservative next steps.

Example future CLI/agent commands:

```bash
workout-pp-cli exercises search bench --limit 5
workout-pp-cli workout start --title "Upper"
workout-pp-cli workout add-bulk --exercise bench "135x8,155x5,165x3"
workout-pp-cli workout recent --exercise bench
workout-pp-cli workout progress --exercise bench
workout-pp-cli workout close --notes "felt solid"
```

## Roadmap

- Dedicated exercise resolve endpoint with confidence and `needs_confirmation`
- Exercise facets endpoint for muscles/equipment/categories
- User exercise preferences for ambiguous phrases
- Static image serving from `public/exercise-images`
- Resolved `image_urls` in exercise responses
- Real recent/progress summaries with volume and estimated 1RM
- Personal records
- CLI for fast workout logging
- Hermes companion skill
- Garmin import for cardio/recovery data
- Cardio sessions: run, walk, bike, row, elliptical, hike
- Workout plans and progression rules

## Specs

- [Lifting Tracker API](docs/superpowers/specs/2026-05-19-lifting-tracker-design.md)
- [Exercise Library API](docs/superpowers/specs/2026-05-19-exercise-library-api.md)

## License

MIT.

