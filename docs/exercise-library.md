# Exercise Library

The exercise library is the lookup layer for workout logging. It lets clients and agents search exercises, resolve shorthand, manage aliases, and remember preferences.

## Exercise Records

Exercises can include:

- name
- category
- equipment
- force
- level
- mechanic
- primary muscles
- secondary muscles
- instructions
- image paths
- resolved image URLs

Example response fields:

```json
{
  "id": 123,
  "source": "free_exercise_db",
  "source_code": "Barbell_Bench_Press",
  "name": "Barbell Bench Press",
  "category": "strength",
  "equipment": "barbell",
  "force": "push",
  "level": "beginner",
  "mechanic": "compound",
  "primary_muscles": ["chest"],
  "secondary_muscles": ["shoulders", "triceps"],
  "image_paths": ["Barbell_Bench_Press/0.jpg"],
  "image_urls": ["http://localhost:8000/exercise-images/Barbell_Bench_Press/0.jpg"],
  "active": true
}
```

## Search

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

Supported filters:

- `equipment`
- `muscle`
- `category`
- `level`
- `mechanic`
- `force`

## Resolve

Use resolution when a user or agent has fuzzy input.

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

The response tells the caller whether it can proceed automatically:

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

If a phrase is ambiguous, the response can ask the client to confirm:

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

## Aliases

Aliases map shorthand to canonical exercises.

```bash
curl -s -X POST "$WT_BASE_URL/exercises/123/aliases" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias": "bench", "source": "user", "confidence": 1.0}'
```

Alias sources:

- `system`
- `user`
- `agent`

## Preferences

Preferences remember how ambiguous phrases should resolve.

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

## Facets

Facets list values present in the exercise database:

```bash
curl -s "$WT_BASE_URL/exercises/facets" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

The response includes:

- categories
- equipment
- muscles
- levels
- mechanics
- forces

