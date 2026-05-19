# Lifting Tracker API — Design Spec

## Overview

Add strength training support to the existing nutrition tracker stack: FastAPI, SQLite, CLI commands, and Hermes as the coaching/interface layer.

The goal is not to build a full fitness app UI. The goal is a durable workout system of record that can be driven by agents and quick CLI commands:

- "log bench 135x8, 155x5, 165x3"
- "what did I squat last time?"
- "show my recent push workouts"
- "what should I lift today?"
- "close out this workout"

The tracker should support fast set logging, recent-history lookup, progression summaries, and simple workout planning without requiring manual spreadsheet work.

## Reference Sources

### free-exercise-db

Repository: https://github.com/yuhonas/free-exercise-db

Use as the primary seed dataset because it is public-domain/Unlicense and has a clean JSON bundle.

Useful data:

- 873 exercise templates
- exercise name
- category
- equipment
- force
- level
- mechanic
- primary muscles
- secondary muscles
- instructions
- image paths

Seed file:

```text
dist/exercises.json
```

Sample source shape:

```json
{
  "id": "3_4_Sit-Up",
  "name": "3/4 Sit-Up",
  "force": "pull",
  "level": "beginner",
  "mechanic": "compound",
  "equipment": "body only",
  "primaryMuscles": ["abdominals"],
  "secondaryMuscles": [],
  "instructions": ["..."],
  "category": "strength",
  "images": ["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"]
}
```

### wger

Repository: https://github.com/wger-project/wger

Use only as architecture/domain-model inspiration. Do not lift code into this MIT project because wger is AGPL-3.0.

Useful model ideas:

- exercise base separated from translations/descriptions
- muscles, equipment, categories
- workout sessions
- workout logs
- target reps/weight versus actual reps/weight
- reps in reserve
- rest targets
- routine/planning concepts

## Core Data Model

### ExerciseTemplate

Seeded from free-exercise-db, then editable locally.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| source | enum | `free_exercise_db`, `custom` |
| source_code | str | External exercise ID, unique with source |
| name | str | Display name |
| normalized_name | str | Search-friendly name |
| category | str | e.g. strength, stretching |
| equipment | str | e.g. barbell, dumbbell, body only |
| force | str | push, pull, static, nullable |
| level | str | beginner/intermediate/expert, nullable |
| mechanic | str | compound/isolation, nullable |
| primary_muscles | JSON | List of muscle names |
| secondary_muscles | JSON | List of muscle names |
| instructions | JSON | Ordered instruction strings |
| image_paths | JSON | Source-relative image paths |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

Indexes:

- unique `(source, source_code)` where source_code is not null
- index on `name`
- FTS index on `name`, `equipment`, `category`, muscles

### ExerciseAlias

Local aliases for agent-friendly matching.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| exercise_template_id | int | FK to ExerciseTemplate |
| alias | str | e.g. "bench", "db row", "ohp" |
| created_at | datetime | Timestamp |

Examples:

- `bench` -> Barbell Bench Press
- `ohp` -> Standing Barbell Shoulder Press
- `lat pulldown` -> Wide-Grip Lat Pulldown

### WorkoutSession

One lifting session.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | Default 1 |
| date | date | Local workout date |
| started_at | datetime | Nullable |
| ended_at | datetime | Nullable |
| title | str | e.g. Push, Pull, Legs, Upper, Lower |
| location | str | Nullable |
| body_weight_kg | float | Nullable snapshot |
| energy_score | int | Nullable 1-10 |
| soreness_score | int | Nullable 1-10 |
| stress_score | int | Nullable 1-10 |
| notes | str | Nullable |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

### WorkoutSet

One logged set. Warmups, working sets, dropsets, and timed/bodyweight work all fit here.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| session_id | int | FK to WorkoutSession |
| exercise_template_id | int | FK to ExerciseTemplate |
| set_number | int | Order within exercise/session |
| set_type | enum | `warmup`, `working`, `drop`, `failure`, `amrap`, `bodyweight`, `timed` |
| weight | float | Nullable |
| weight_unit | enum | `lb`, `kg`, nullable |
| reps | float | Nullable, supports partials or non-integer units if needed |
| duration_seconds | int | Nullable |
| distance | float | Nullable for carries/cardio-like work |
| distance_unit | enum | `m`, `ft`, `mi`, nullable |
| rpe | float | Nullable 1-10 |
| rir | float | Nullable reps in reserve |
| rest_seconds | int | Nullable |
| notes | str | Nullable |
| performed_at | datetime | Nullable |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

Rules:

- At least one of `reps`, `duration_seconds`, or `distance` must be present.
- `weight_unit` is required if `weight` is present.
- Set ordering should be stable and editable.

### WorkoutPlan

Optional v2 planning layer. MVP can log ad hoc sessions without formal plans.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | Default 1 |
| name | str | e.g. Linear Progression, Push Pull Legs |
| notes | str | Nullable |
| active | bool | Whether currently used |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

### WorkoutPlanItem

Optional v2 planned exercise prescription.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| plan_id | int | FK to WorkoutPlan |
| day_name | str | e.g. Push A, Lower B |
| exercise_template_id | int | FK |
| order_index | int | Order in workout |
| target_sets | int | Nullable |
| target_reps_min | int | Nullable |
| target_reps_max | int | Nullable |
| target_weight | float | Nullable |
| target_weight_unit | enum | `lb`, `kg`, nullable |
| target_rpe | float | Nullable |
| target_rir | float | Nullable |
| rest_seconds | int | Nullable |
| progression_rule | str | Nullable text rule |

## API Endpoints

### Exercise Search

```http
GET /exercises/search?q=bench&limit=10
GET /exercises/{id}
POST /exercises
PATCH /exercises/{id}
DELETE /exercises/{id}
POST /exercises/{id}/aliases
DELETE /exercises/aliases/{alias_id}
```

Search should match:

- exercise name
- aliases
- equipment
- category
- primary/secondary muscles

### Exercise Import

```http
POST /imports/exercises/free-exercise-db
```

For production, prefer a CLI/script import rather than uploading a large JSON file through HTTP:

```bash
python -m scripts.import_exercises /path/to/free-exercise-db/dist/exercises.json
```

Import behavior:

- Upsert by `(source, source_code)`
- Preserve local aliases
- Do not delete custom exercises
- Store source-relative image paths

### Workout Sessions

```http
POST /workouts/sessions
GET /workouts/sessions/{id}
GET /workouts/sessions?start=2026-05-01&end=2026-05-19
PATCH /workouts/sessions/{id}
DELETE /workouts/sessions/{id}
POST /workouts/sessions/{id}/close
```

### Workout Sets

```http
POST /workouts/sessions/{session_id}/sets
PATCH /workouts/sets/{set_id}
DELETE /workouts/sets/{set_id}
POST /workouts/sessions/{session_id}/sets/bulk
```

Bulk set logging is important for CLI/Hermes:

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

### Workout History And Progress

```http
GET /workouts/recent?exercise_id=123&limit=5
GET /workouts/progress?exercise_id=123&start=2026-01-01&end=2026-05-19
GET /workouts/personal-records
GET /workouts/summary?start=2026-05-01&end=2026-05-19
```

Progress response should include:

- recent top sets
- estimated 1RM
- total volume
- best volume session
- number of sessions
- average reps/weight

Estimated 1RM:

```text
e1RM = weight * (1 + reps / 30)
```

Use Epley for MVP. Make formulas swappable later.

## CLI Commands

The CLI should optimize for very fast logging.

```bash
nutrition-pp-cli exercises search bench --limit 5
nutrition-pp-cli workout start --title "Upper"
nutrition-pp-cli workout add-set --exercise bench --weight 135 --lb --reps 8
nutrition-pp-cli workout add-bulk --exercise bench "135x8,155x5,165x3"
nutrition-pp-cli workout recent --exercise bench
nutrition-pp-cli workout progress --exercise bench
nutrition-pp-cli workout close --notes "felt solid"
nutrition-pp-cli workout today
```

Agent-friendly JSON mode:

```bash
nutrition-pp-cli workout today --agent
nutrition-pp-cli workout recent --exercise squat --agent
nutrition-pp-cli workout progress --exercise deadlift --agent
```

Parsing shorthand:

- `135x8` -> 135 lb x 8 reps by default if user preference is lb
- `60kgx5` -> 60 kg x 5 reps
- `bw x 12` -> bodyweight x 12 reps
- `plank 60s` -> timed set

## Hermes Skill Behavior

Hermes should load the lifting skill when the user says things like:

- "log this workout"
- "I lifted"
- "bench 135x8"
- "what did I squat last time?"
- "what should I lift today?"
- "how is my lifting progressing?"
- "close out my workout"

Expected workflows:

### Fast Set Logging

User:

```text
bench 135x8, 155x5, 165x3
```

Hermes:

1. Finds or creates today's open workout session.
2. Resolves `bench` through aliases/search.
3. Logs three sets.
4. Returns concise confirmation with last-session comparison.

### Workout Closeout

User:

```text
close out lifting. Felt tired but got it done.
```

Hermes:

1. Closes active session.
2. Adds notes.
3. Summarizes total sets, top lifts, estimated PRs, and recovery flags.

### Progress Review

User:

```text
how is bench going?
```

Hermes:

1. Queries recent/progress endpoints.
2. Reports trend, best recent set, e1RM trend, and conservative next-step suggestion.
3. Uses recovery/rhythm tone, not shame.

## MVP Build Order

1. Add exercise template schema, repository, models, routes, and search.
2. Add `scripts/import_exercises.py` for free-exercise-db JSON.
3. Add workout session schema, repository, models, routes.
4. Add workout set schema, repository, models, routes.
5. Add bulk set logging endpoint.
6. Add recent/progress endpoints with volume and Epley e1RM.
7. Add CLI commands for exercise search, workout start, add-set, add-bulk, recent, progress, close.
8. Add README section for exercise dataset import.
9. Add Hermes `pp-lifting` or extend `pp-nutrition` into `pp-health`.

## Design Decisions

- Keep lifting inside the existing API repo for now. It shares auth, user ID, deployment, SQLite, CLI, and Hermes patterns.
- Use public-domain free-exercise-db data for seed names and metadata.
- Do not copy wger code because of AGPL. Use it only as domain-model reference.
- Default weight unit should be user-configurable; MVP can assume `lb`.
- Allow ad hoc sessions before formal workout plans. Logging is more important than planning.
- Store full set history; derive progress summaries rather than storing aggregates first.
- Keep the API boring and explicit. Let Hermes handle natural language and coaching.

## Deferred

- Formal program builder with progression rules.
- Plate calculator.
- Rest timer integration.
- Apple Health workout import/export.
- Garmin/Strava/Hevy import.
- Exercise images hosted locally or mirrored.
- Superset/circuit grouping.
- Per-exercise technique notes.
- Injury/pain tracking per movement.
- Auto-generated workout recommendations.

