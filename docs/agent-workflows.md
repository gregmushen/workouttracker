# Agent Workflows

Workout Tracker is designed to be easy for agents and CLIs to use.

The API keeps the durable data explicit. The agent handles natural language, clarification, reminders, and coaching tone.

## Fast Set Logging

User:

```text
bench 135x8, 155x5, 165x3
```

Agent flow:

1. Call `POST /exercises/resolve` with `bench`.
2. If `needs_confirmation` is false, create or find today's session.
3. Call `POST /workouts/sessions/{id}/sets/bulk`.
4. Confirm what was logged.
5. Optionally call recent/progress endpoints for comparison.

## Ambiguous Exercise

User:

```text
row 80x10
```

Agent flow:

1. Call `POST /exercises/resolve` with `row`.
2. If `needs_confirmation` is true, show the top alternatives.
3. Ask the user which exercise they mean.
4. Log the set.
5. Create a preference if the user wants that phrase remembered.

## Example Resolve Request

```json
{
  "query": "row",
  "context": {
    "equipment_available": ["dumbbell", "barbell", "cable"],
    "recent_exercise_ids": [10, 11],
    "session_title": "Pull",
    "goal": "hypertrophy"
  }
}
```

## Example Bulk Log Request

```json
{
  "exercise_query": "bench",
  "sets": [
    {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working", "rpe": 7},
    {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working", "rpe": 8},
    {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working", "rpe": 8.5}
  ]
}
```

## Daily Closeout

User:

```text
close out lifting. Felt tired but got it done.
```

Agent flow:

1. Find the active or most recent session.
2. Call `/workouts/sessions/{id}/close`.
3. Include notes and recovery scores if provided.
4. Summarize total sets, top lifts, and any PRs.

## Progress Review

User:

```text
how is bench going?
```

Agent flow:

1. Resolve `bench`.
2. Call `/workouts/recent`.
3. Call `/workouts/progress`.
4. Summarize trend, recent best set, estimated 1RM, and volume.

## Recommended Agent Behavior

- Ask for confirmation when `needs_confirmation` is true.
- Store preferences only after the user chooses a mapping.
- Keep confirmations short.
- Treat RPE/RIR as subjective, not as failure.
- Prefer conservative progression suggestions when stress, soreness, or fatigue is high.
- Do not overwrite logged sets without explicit user instruction.

