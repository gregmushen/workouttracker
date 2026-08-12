# Workout Logging

Workout logging is organized around sessions and sets.

## Sessions

A session is one workout on one date.

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

Session fields:

- `date`
- `title`
- `location`
- `started_at`
- `body_weight_kg`
- `energy_score`
- `soreness_score`
- `stress_score`
- `notes`

## Sets

A set belongs to a session and an exercise.

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

Set fields:

- `exercise_template_id`
- `set_number`
- `set_type`
- `weight`
- `weight_unit`
- `reps`
- `duration_seconds`
- `distance`
- `distance_unit`
- `rpe`
- `rir`
- `rest_seconds`
- `avg_watts`
- `avg_heart_rate_bpm`
- `max_heart_rate_bpm`
- `calories_kcal`
- `avg_cadence_rpm`
- `notes`
- `performed_at`

At least one of `reps`, `duration_seconds`, or `distance` is required.

If `weight` is present, `weight_unit` is required.

## Set Types

Supported set types:

- `warmup`
- `working`
- `drop`
- `failure`
- `amrap`
- `bodyweight`
- `timed`

Examples:

```json
{"set_type": "warmup", "weight": 95, "weight_unit": "lb", "reps": 8}
{"set_type": "working", "weight": 135, "weight_unit": "lb", "reps": 8, "rpe": 7.5}
{"set_type": "amrap", "weight": 135, "weight_unit": "lb", "reps": 13, "rpe": 10}
{"set_type": "timed", "duration_seconds": 60, "notes": "plank"}
{"set_type": "bodyweight", "reps": 10}
```

## Cardio Metrics

Timed cardio sets (indoor cycling, rowing, treadmill) accept structured metrics
instead of stuffing them into `notes`. All are optional and nullable.

| Field | Meaning |
| --- | --- |
| `avg_watts` | Average power output in watts |
| `avg_heart_rate_bpm` | Average heart rate |
| `max_heart_rate_bpm` | Peak heart rate |
| `calories_kcal` | Bike-reported or user-entered calories (never calculated) |
| `avg_cadence_rpm` | Average cycling cadence |

```json
{"set_type": "timed", "duration_seconds": 3600, "avg_watts": 60,
 "avg_heart_rate_bpm": 120, "max_heart_rate_bpm": 135,
 "calories_kcal": 225, "avg_cadence_rpm": 82, "rpe": 4}
```

## RPE

RPE means rating of perceived exertion. Higher means harder.

| RPE | Meaning |
|---|---|
| 6 | Easy, many reps left |
| 7 | Moderately hard, about 3 reps left |
| 8 | Hard, about 2 reps left |
| 9 | Very hard, about 1 rep left |
| 10 | Max effort, no reps left |

## RIR

RIR means reps in reserve. It estimates how many more reps you could have done.

Examples:

```json
{"weight": 135, "weight_unit": "lb", "reps": 8, "rpe": 8}
{"weight": 135, "weight_unit": "lb", "reps": 8, "rir": 2}
```

Those are roughly equivalent. An RPE 8 set usually means about 2 reps in reserve.

## Bulk Logging

Bulk logging resolves the exercise query and creates several sets.

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

Timed set:

```json
{
  "exercise_query": "plank",
  "sets": [
    {"set_type": "timed", "duration_seconds": 60, "rpe": 8}
  ]
}
```

Bodyweight sets:

```json
{
  "exercise_query": "pullups",
  "sets": [
    {"set_type": "bodyweight", "reps": 8, "rir": 2},
    {"set_type": "bodyweight", "reps": 7, "rir": 1},
    {"set_type": "bodyweight", "reps": 6, "rpe": 9}
  ]
}
```

## Close A Session

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

## Progress

Recent sets:

```bash
curl -s "$WT_BASE_URL/workouts/recent?exercise_id=123&limit=5" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Progress:

```bash
curl -s "$WT_BASE_URL/workouts/progress?exercise_id=123&start=2026-01-01&end=2026-05-19" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

Personal records:

```bash
curl -s "$WT_BASE_URL/workouts/personal-records" \
  -H "Authorization: Bearer $WT_BEARER_TOKEN"
```

