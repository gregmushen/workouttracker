# Exercise Library API — Design Spec

## Overview

Build a first-class exercise library API for AI-assisted workout logging and planning.

The exercise library is not just seed data. It is the lookup, search, and disambiguation layer that lets Hermes understand phrases like:

- "bench"
- "db row"
- "chest exercise with dumbbells"
- "something for hamstrings"
- "log pullups 8, 7, 6"
- "what did I do for shoulders last week?"

The library should be optimized for agent use: fast search, clear filters, aliases, confidence scores, and a resolution endpoint that can decide when to use a match versus ask for clarification.

## Goals

- Import a large public-domain exercise dataset.
- Provide searchable exercise names, muscles, equipment, categories, mechanics, and instructions.
- Support local aliases and preferred mappings.
- Let agents resolve fuzzy user language to canonical exercise IDs.
- Preserve custom exercises and local edits.
- Provide enough metadata for workout planning and substitutions.

## Non-Goals

- Do not build a public exercise encyclopedia UI in MVP.
- Do not copy AGPL code from wger.
- Do not depend on paid/private exercise APIs.
- Do not store image binaries in SQLite.

## Data Source

Primary seed source:

```text
https://github.com/yuhonas/free-exercise-db
```

License: Unlicense/public domain.

Seed file:

```text
dist/exercises.json
```

Observed size:

```text
873 exercises
```

Source fields:

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

Secondary reference:

```text
https://github.com/wger-project/wger
```

Use only for conceptual reference. wger is AGPL-3.0.

## Data Model

### Exercise

Canonical exercise record.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| source | enum | `free_exercise_db`, `custom` |
| source_code | str | External ID, nullable for custom |
| name | str | Canonical display name |
| normalized_name | str | Lowercase/search-normalized name |
| category | str | e.g. strength, stretching |
| equipment | str | e.g. barbell, dumbbell, body only |
| force | str | push, pull, static, nullable |
| level | str | beginner, intermediate, expert, nullable |
| mechanic | str | compound, isolation, nullable |
| primary_muscles | JSON | List of muscle slugs/names |
| secondary_muscles | JSON | List of muscle slugs/names |
| instructions | JSON | Ordered instruction strings |
| image_paths | JSON | Source-relative public image paths |
| image_urls | virtual | Resolved public URLs in API responses |
| active | bool | False hides deprecated records |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

Indexes:

- unique `(source, source_code)` where `source_code` is not null
- index `normalized_name`
- index `category`
- index `equipment`
- FTS index across `name`, `aliases`, `category`, `equipment`, `primary_muscles`, `secondary_muscles`

### ExerciseAlias

User/system alias for an exercise.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| exercise_id | int | FK to Exercise |
| alias | str | e.g. `bench`, `ohp`, `db row` |
| normalized_alias | str | Search-normalized alias |
| source | enum | `system`, `user`, `agent` |
| confidence | float | Optional, default 1.0 for explicit aliases |
| created_at | datetime | Timestamp |

Rules:

- User aliases outrank system aliases.
- Exact alias match should usually resolve without confirmation.
- Ambiguous aliases can map to multiple exercises, but should require confirmation unless a preferred exercise is set.

### ExercisePreference

Personal preference layer for ambiguous exercise names.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | Default 1 |
| phrase | str | e.g. `bench`, `row`, `press` |
| normalized_phrase | str | Search-normalized phrase |
| preferred_exercise_id | int | FK to Exercise |
| context | JSON | Optional equipment/program context |
| created_at | datetime | Timestamp |
| updated_at | datetime | Timestamp |

Examples:

- `bench` -> Barbell Bench Press
- `press` -> Standing Barbell Shoulder Press
- `row` + context `{equipment: "dumbbell"}` -> One-Arm Dumbbell Row

### ExerciseSearchLog

Optional diagnostic table for improving aliases/resolution.

| Field | Type | Notes |
|---|---|---|
| id | int | Primary key |
| user_id | int | Default 1 |
| query | str | Raw query |
| matched_exercise_id | int | Nullable |
| confidence | float | Nullable |
| required_confirmation | bool | Whether agent had to ask |
| created_at | datetime | Timestamp |

## API Endpoints

## Static Image Files

Exercise images should live in static public files, not in SQLite and not in private data volumes.

Expected layout:

```text
public/
  exercise-images/
    3_4_Sit-Up/
      0.jpg
      1.jpg
```

Public URL shape:

```http
GET /exercise-images/{exercise_image_path}
```

Example:

```text
/exercise-images/3_4_Sit-Up/0.jpg
/exercise-images/3_4_Sit-Up/1.jpg
```

The database stores only dataset-relative image paths:

```json
["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"]
```

The API resolves those paths into public URLs at response time:

```json
{
  "image_paths": ["3_4_Sit-Up/0.jpg", "3_4_Sit-Up/1.jpg"],
  "image_urls": [
    "https://workouts.paracosmlab.com/exercise-images/3_4_Sit-Up/0.jpg",
    "https://workouts.paracosmlab.com/exercise-images/3_4_Sit-Up/1.jpg"
  ]
}
```

This lets Hermes or any future UI show form images without bloating the database.

### Search

```http
GET /exercises/search?q=bench&limit=10
```

Query parameters:

| Param | Type | Notes |
|---|---|---|
| q | str | Search text |
| limit | int | Default 10 |
| equipment | str | Optional filter |
| muscle | str | Optional primary/secondary muscle filter |
| category | str | Optional filter |
| level | str | Optional filter |
| mechanic | str | Optional filter |
| force | str | Optional filter |

Response:

```json
{
  "query": "bench",
  "results": [
    {
      "id": 123,
      "name": "Barbell Bench Press",
      "category": "strength",
      "equipment": "barbell",
      "primary_muscles": ["chest"],
      "secondary_muscles": ["triceps", "shoulders"],
      "image_urls": [
        "https://workouts.paracosmlab.com/exercise-images/Barbell_Bench_Press/0.jpg"
      ],
      "score": 0.94,
      "match_reason": "exact alias"
    }
  ]
}
```

Ranking signals:

1. Exact user preference
2. Exact alias
3. Exact normalized name
4. Prefix match
5. Full-text match
6. Muscle/equipment/category fit
7. Recently used exercise

### Resolve

```http
POST /exercises/resolve
```

Purpose: let an AI turn fuzzy user language into one canonical exercise ID.

Request:

```json
{
  "query": "bench",
  "context": {
    "equipment_available": ["barbell", "dumbbell"],
    "recent_exercise_ids": [123, 456],
    "session_title": "Upper",
    "goal": "strength"
  }
}
```

Response:

```json
{
  "query": "bench",
  "best_match": {
    "id": 123,
    "name": "Barbell Bench Press",
    "confidence": 0.94,
    "match_reason": "exact user alias"
  },
  "alternatives": [
    {
      "id": 456,
      "name": "Dumbbell Bench Press",
      "confidence": 0.78,
      "match_reason": "name match"
    }
  ],
  "needs_confirmation": false,
  "confirmation_prompt": null
}
```

Ambiguous response:

```json
{
  "query": "row",
  "best_match": null,
  "alternatives": [
    {"id": 10, "name": "Bent Over Barbell Row", "confidence": 0.74},
    {"id": 11, "name": "One-Arm Dumbbell Row", "confidence": 0.72},
    {"id": 12, "name": "Seated Cable Row", "confidence": 0.70}
  ],
  "needs_confirmation": true,
  "confirmation_prompt": "Which row do you mean: barbell row, dumbbell row, or cable row?"
}
```

Resolve rules:

- `confidence >= 0.90`: resolve automatically.
- `0.75 <= confidence < 0.90`: resolve automatically only if recent usage or preference supports it.
- `< 0.75`: ask for confirmation.
- If top two candidates are within 0.08 confidence, ask unless a user preference exists.

### CRUD

```http
GET /exercises/{id}
POST /exercises
PATCH /exercises/{id}
DELETE /exercises/{id}
```

Delete should soft-delete by setting `active = false`.

### Aliases

```http
GET /exercises/{id}/aliases
POST /exercises/{id}/aliases
DELETE /exercises/aliases/{alias_id}
```

Create alias request:

```json
{
  "alias": "bench",
  "source": "user"
}
```

### Preferences

```http
GET /exercises/preferences
POST /exercises/preferences
PATCH /exercises/preferences/{id}
DELETE /exercises/preferences/{id}
```

Create preference request:

```json
{
  "phrase": "bench",
  "preferred_exercise_id": 123,
  "context": {
    "equipment": "barbell"
  }
}
```

### Facets

```http
GET /exercises/facets
```

Response:

```json
{
  "categories": ["strength", "stretching", "plyometrics"],
  "equipment": ["barbell", "dumbbell", "body only", "cable"],
  "muscles": ["chest", "lats", "quadriceps", "hamstrings"],
  "levels": ["beginner", "intermediate", "expert"],
  "mechanics": ["compound", "isolation"],
  "forces": ["push", "pull", "static"]
}
```

## Import Script

```bash
python -m scripts.import_exercises /path/to/free-exercise-db/dist/exercises.json
```

Behavior:

- Validate JSON shape.
- Upsert exercises by `(source, source_code)`.
- Normalize names and aliases.
- Store arrays as JSON.
- Copy referenced image files into `public/exercise-images/` or verify they are already present there.
- Store only public relative image paths in the database.
- Preserve local custom exercises.
- Preserve user aliases and preferences.
- Do not hard-delete missing imported exercises; mark inactive only with explicit `--deactivate-missing`.

Options:

```bash
python -m scripts.import_exercises data/exercises.json
python -m scripts.import_exercises data/exercises.json --images-root /path/to/free-exercise-db/exercises --public-images-root public/exercise-images
python -m scripts.import_exercises data/exercises.json --deactivate-missing
python -m scripts.import_exercises data/exercises.json --dry-run
```

Output:

```text
Imported 873 exercises
Created 873
Updated 0
Skipped 0
```

## Built-In Alias Seeding

Add a small curated alias file for common lifting shorthand.

```json
[
  {"alias": "bench", "exercise_name": "Barbell Bench Press"},
  {"alias": "ohp", "exercise_name": "Standing Barbell Shoulder Press"},
  {"alias": "squat", "exercise_name": "Barbell Squat"},
  {"alias": "deadlift", "exercise_name": "Barbell Deadlift"},
  {"alias": "pullups", "exercise_name": "Pullups"},
  {"alias": "lat pulldown", "exercise_name": "Wide-Grip Lat Pulldown"}
]
```

If the exact exercise name is not present in the seed data, skip and report the alias for manual review.

## CLI Commands

```bash
workout-pp-cli exercises search bench --limit 5
workout-pp-cli exercises get 123
workout-pp-cli exercises resolve bench --agent
workout-pp-cli exercises aliases add 123 bench
workout-pp-cli exercises preferences set bench 123
workout-pp-cli exercises facets
workout-pp-cli imports exercises /path/to/exercises.json
```

Agent mode should return compact JSON with IDs, confidence, match reason, and whether confirmation is needed.

## Hermes Behavior

Hermes should use the exercise library before logging workout sets.

Workflow:

1. User says: `bench 135x8`.
2. Hermes calls `resolve("bench")`.
3. If `needs_confirmation = false`, Hermes logs the set with the returned exercise ID.
4. If ambiguous, Hermes asks once.
5. After user chooses, Hermes creates an alias/preference so the same ambiguity does not recur.

Examples:

User:

```text
log row 80x10
```

Hermes:

```text
Which row do you mean: dumbbell row, barbell row, or cable row?
```

User:

```text
dumbbell row
```

Hermes:

1. Logs the set.
2. Stores preference: `row` -> dumbbell row, optionally within current context.

## MVP Build Order

1. Add `exercises` table and FTS index.
2. Add `exercise_aliases` table.
3. Add import script for `free-exercise-db`.
4. Add static public serving for `public/exercise-images`.
5. Add image-copy/verification support to the import script.
6. Add search endpoint with resolved `image_urls`.
7. Add resolve endpoint with simple deterministic ranking.
8. Add CRUD endpoints.
9. Add alias endpoints.
10. Add facets endpoint.
11. Add CLI commands.
12. Add Hermes skill guidance.

## Acceptance Criteria

- Import all 873 seed exercises.
- Search `bench` returns bench press variants.
- Exercise responses include public `image_urls` when images exist.
- Search by muscle/equipment works.
- Resolve exact aliases without confirmation.
- Resolve ambiguous terms with `needs_confirmation = true`.
- User-created aliases affect future resolution.
- Workout logging can depend on exercise IDs from this API.

## Deferred

- Vector embeddings for semantic search.
- Exercise substitution recommendations.
- Injury-aware exercise filtering.
- Equipment-profile filtering by gym/home setup.
- Multi-language exercise names.
- Agent-generated custom exercise creation from natural language.
- Versioned exercise dataset updates.
