# Workout Tracker Documentation

Workout Tracker is a FastAPI backend for strength training data. It is built for people and agents that need a simple, reliable API for exercises, workout sessions, sets, effort tracking, and progress summaries.

It also ships with a lightweight vanilla JavaScript web UI served by the same FastAPI process. The API remains the source of truth; the UI is a thin control surface for quick logging and review.

## Documentation

- [Getting Started](getting-started.md)
- [API Guide](api.md)
- [Exercise Library](exercise-library.md)
- [Workout Logging](workout-logging.md)
- [Exercise Data Import](exercise-data.md)
- [Agent Workflows](agent-workflows.md)
- [Deployment](deployment.md)

## OpenAPI

Run the server and open:

```text
/
/today
```

For agents and API clients, open:

```text
/openapi.json
```

FastAPI also provides interactive docs at:

```text
/docs
/redoc
```
