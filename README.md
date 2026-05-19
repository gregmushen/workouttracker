# Workout Tracker

A personal strength-training API for logging workouts, searching exercises, and giving AI agents a reliable system of record.

Workout Tracker exists because most fitness apps are optimized for screens, taps, and dashboards. This project is optimized for structured data and fast interaction. It gives you a small API that can be driven by a CLI, automation, or an AI coach:

```text
bench 135x8, 155x5, 165x3
what did I squat last time?
show chest exercises with dumbbells
close out this workout, felt tired but steady
```

The API handles the durable facts: exercises, aliases, workout sessions, sets, effort, and progress. An agent or client can handle the conversation.

Workout Tracker also includes a lightweight web UI. The UI is intentionally thin: it sits on top of the same API and gives you a quick human control surface for today's session, exercise search, session review, and progress checks.

## What It Tracks

Workout Tracker supports:

- exercise templates from a public-domain exercise database
- custom exercises
- exercise aliases such as `bench`, `ohp`, `db row`, or `lat pulldown`
- fuzzy exercise resolution for AI workflows
- workout sessions with date, title, location, notes, and recovery context
- workout sets with weight, reps, RPE, RIR, rest, duration, and distance
- bulk set logging by exercise query
- recent exercise history
- progress summaries
- estimated 1RM
- personal records
- static exercise images

## Core Concepts

### Exercises

Exercises are canonical movements such as `Barbell Bench Press`, `Goblet Squat`, or `One-Arm Dumbbell Row`.

Exercises can include:

- category
- equipment
- force
- difficulty level
- mechanic: compound or isolation
- primary muscles
- secondary muscles
- instructions
- image paths and resolved image URLs

### Aliases

Aliases map your shorthand to a canonical exercise.

Examples:

```text
bench -> Barbell Bench Press
ohp -> Standing Barbell Shoulder Press
db row -> One-Arm Dumbbell Row
pullups -> Pullups
```

Aliases matter because agents should not need to ask the same clarification every time.

### Preferences

Preferences remember what you mean by ambiguous phrases.

For example, `row` could mean:

- Barbell Row
- One-Arm Dumbbell Row
- Seated Cable Row

If you pick dumbbell row once, the API can remember that preference.

### RPE And RIR

Workout Tracker supports both RPE and RIR on sets.

RPE means "rating of perceived exertion." A higher number means the set felt harder.

Common interpretation:

| RPE | Meaning |
|---|---|
| 6 | Easy, many reps left |
| 7 | Moderately hard, about 3 reps left |
| 8 | Hard, about 2 reps left |
| 9 | Very hard, about 1 rep left |
| 10 | Max effort, no reps left |

RIR means "reps in reserve." It estimates how many more reps you could have done.

Examples:

```json
{"weight": 135, "weight_unit": "lb", "reps": 8, "rpe": 8}
{"weight": 135, "weight_unit": "lb", "reps": 8, "rir": 2}
```

Those two examples are roughly equivalent: an RPE 8 set usually means about 2 reps in reserve.

### Set Types

Supported set types:

```text
warmup
working
drop
failure
amrap
bodyweight
timed
```

Examples:

```json
{"set_type": "warmup", "weight": 95, "weight_unit": "lb", "reps": 8}
{"set_type": "working", "weight": 135, "weight_unit": "lb", "reps": 8, "rpe": 7.5}
{"set_type": "amrap", "weight": 135, "weight_unit": "lb", "reps": 13, "rpe": 10}
{"set_type": "timed", "duration_seconds": 60, "notes": "plank"}
{"set_type": "bodyweight", "reps": 10}
```

## API

All endpoints except `/health` require:

```http
Authorization: Bearer <token>
```

Useful environment variables for examples:

```bash
export WT_BASE_URL="http://localhost:8000"
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
```

### Health And OpenAPI

```http
GET /health
GET /openapi.json
```

```bash
curl -s "$WT_BASE_URL/health"
curl -s "$WT_BASE_URL/openapi.json"
```

### Search Exercises

Search by name:

```bash
curl -s "$WT_BASE_URL/exercises/search?q=bench&limit=5" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Search by equipment:

```bash
curl -s "$WT_BASE_URL/exercises/search?q=press&equipment=dumbbell" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Search by muscle:

```bash
curl -s "$WT_BASE_URL/exercises/search?q=&muscle=hamstrings" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Search with several filters:

```bash
curl -s "$WT_BASE_URL/exercises/search?q=row&equipment=dumbbell&category=strength" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Exercise responses include `image_urls` when image paths exist.

### Resolve An Exercise

Use `POST /exercises/resolve` when an agent needs to turn fuzzy user language into a canonical exercise ID.

```bash
curl -s -X POST "$WT_BASE_URL/exercises/resolve" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "bench",
    "context": {
      "equipment_available": ["barbell", "dumbbell"],
      "recent_exercise_ids": [],
      "session_title": "Upper",
      "goal": "strength"
    }
  }'
```

Response shape:

```json
{
  "query": "bench",
  "best_match": {
    "id": 123,
    "name": "Barbell Bench Press",
    "confidence": 0.94,
    "match_reason": "exact alias"
  },
  "alternatives": [],
  "needs_confirmation": false,
  "confirmation_prompt": null
}
```

Ambiguous terms can return `needs_confirmation: true` with alternatives:

```json
{
  "query": "row",
  "best_match": null,
  "alternatives": [
    {"id": 10, "name": "Bent Over Barbell Row", "confidence": 0.82, "match_reason": "full-text match"},
    {"id": 11, "name": "One-Arm Dumbbell Row", "confidence": 0.78, "match_reason": "full-text match"}
  ],
  "needs_confirmation": true,
  "confirmation_prompt": "Which exercise do you mean: Bent Over Barbell Row, One-Arm Dumbbell Row?"
}
```

### Facets

List available categories, equipment, muscles, levels, mechanics, and force values:

```bash
curl -s "$WT_BASE_URL/exercises/facets" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

### Aliases

Add an alias:

```bash
curl -s -X POST "$WT_BASE_URL/exercises/123/aliases" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias": "bench", "source": "user", "confidence": 1.0}'
```

List aliases:

```bash
curl -s "$WT_BASE_URL/exercises/123/aliases" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Delete an alias:

```bash
curl -s -X DELETE "$WT_BASE_URL/exercises/aliases/456" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

### Preferences

Create or update a preference:

```bash
curl -s -X POST "$WT_BASE_URL/exercises/preferences" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phrase": "row",
    "preferred_exercise_id": 123,
    "context": {"equipment": "dumbbell"}
  }'
```

List preferences:

```bash
curl -s "$WT_BASE_URL/exercises/preferences" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

### Create A Workout Session

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-19",
    "title": "Upper",
    "location": "garage",
    "energy_score": 7,
    "soreness_score": 3,
    "stress_score": 4,
    "notes": "Felt steady."
  }'
```

### Log One Set

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions/1/sets" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_template_id": 123,
    "set_number": 1,
    "set_type": "working",
    "weight": 135,
    "weight_unit": "lb",
    "reps": 8,
    "rpe": 8,
    "rir": 2,
    "rest_seconds": 120
  }'
```

### Bulk Log Sets

Use bulk set logging when the client or agent already knows the exercise phrase.

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions/1/sets/bulk" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "bench",
    "sets": [
      {"weight": 95, "weight_unit": "lb", "reps": 8, "set_type": "warmup"},
      {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working", "rpe": 7},
      {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working", "rpe": 8},
      {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working", "rpe": 8.5}
    ]
  }'
```

Timed example:

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions/1/sets/bulk" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "plank",
    "sets": [
      {"set_type": "timed", "duration_seconds": 60, "rpe": 8}
    ]
  }'
```

Bodyweight example:

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions/1/sets/bulk" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "pullups",
    "sets": [
      {"set_type": "bodyweight", "reps": 8, "rir": 2},
      {"set_type": "bodyweight", "reps": 7, "rir": 1},
      {"set_type": "bodyweight", "reps": 6, "rpe": 9}
    ]
  }'
```

### Close A Session

```bash
curl -s -X POST "$WT_BASE_URL/workouts/sessions/1/close" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Good session. Bench moved well, rows felt heavy.",
    "energy_score": 7,
    "soreness_score": 4,
    "stress_score": 3
  }'
```

### Recent History And Progress

Recent sets for an exercise:

```bash
curl -s "$WT_BASE_URL/workouts/recent?exercise_id=123&limit=5" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Progress over time:

```bash
curl -s "$WT_BASE_URL/workouts/progress?exercise_id=123&start=2026-01-01&end=2026-05-19" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Personal records:

```bash
curl -s "$WT_BASE_URL/workouts/personal-records" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Workout summary:

```bash
curl -s "$WT_BASE_URL/workouts/summary?start=2026-05-01&end=2026-05-19" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

## Agent Workflow

A typical AI workflow looks like this:

1. User says: `bench 135x8, 155x5, 165x3`.
2. Agent calls `/exercises/resolve` with `bench`.
3. If `needs_confirmation` is false, agent creates or finds today's session.
4. Agent calls `/workouts/sessions/{id}/sets/bulk`.
5. Agent reports what was logged and optionally compares it to recent history.

For ambiguous input:

1. User says: `row 80x10`.
2. Agent calls `/exercises/resolve` with `row`.
3. API returns alternatives and `needs_confirmation: true`.
4. Agent asks which row.
5. User chooses.
6. Agent logs the set and creates a preference so future `row` inputs resolve cleanly.

## Exercise Data

This project uses [free-exercise-db](https://github.com/yuhonas/free-exercise-db) as the seed exercise dataset.

Credit:

- Project: `free-exercise-db`
- Repository: https://github.com/yuhonas/free-exercise-db
- License: Unlicense / public domain
- Data used: exercise names, categories, equipment, force, level, mechanic, primary/secondary muscles, instructions, and image paths

Download the exercise JSON:

```bash
mkdir -p data
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

Exercise images are served from public static files:

```text
public/
  exercise-images/
    3_4_Sit-Up/
      0.jpg
      1.jpg
```

The database stores relative paths:

```json
["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"]
```

API responses resolve those paths into `image_urls` using `WT_PUBLIC_BASE_URL` or the request base URL.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Start the packaged app:

```bash
workouttracker serve --db ./data/workout.db --token replace-with-a-long-random-token
```

Then open:

```text
http://127.0.0.1:8000
```

Useful CLI commands:

```bash
workouttracker migrate --db ./data/workout.db
workouttracker import-exercises /path/to/free-exercise-db/dist/exercises.json --db ./data/workout.db
workouttracker version
```

Set environment:

```bash
export WT_BEARER_TOKEN="replace-with-a-long-random-token"
export WT_DB_PATH="./data/workout.db"
export WT_PUBLIC_BASE_URL="http://localhost:8000"
```

Run migrations:

```bash
alembic upgrade head
```

Run the server:

```bash
uvicorn app.main:app --reload
```

The FastAPI app serves both the REST API and the vanilla JavaScript UI. API docs remain available at `/docs`, `/redoc`, and `/openapi.json`.

Run checks:

```bash
pytest tests/
ruff check app scripts tests alembic
```

## Stack

- Python 3.12
- FastAPI
- SQLite
- Alembic
- Pytest
- Ruff
- Docker/Kamal-compatible deployment

## Deployment Configuration

The included Kamal/Woodpecker files are parameterized. Set these secrets or environment variables in your CI/deploy environment:

```text
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
REGISTRY_SERVER
REGISTRY_USERNAME
KAMAL_REGISTRY_PASSWORD
APP_HOST
WT_BEARER_TOKEN
CLOUDFLARE_TUNNEL_TOKEN
```

The default image/service name is `workouttracker`.

## Documentation

- [Getting Started](docs/getting-started.md)
- [API Guide](docs/api.md)
- [Exercise Library](docs/exercise-library.md)
- [Workout Logging](docs/workout-logging.md)
- [Exercise Data Import](docs/exercise-data.md)
- [Agent Workflows](docs/agent-workflows.md)
- [Deployment](docs/deployment.md)

## License

MIT. See [LICENSE](LICENSE).
