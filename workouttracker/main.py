from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from workouttracker.auth import require_auth
from workouttracker.config import settings
from workouttracker.database import get_connection, init_schema
from workouttracker.repositories.exercises import ExerciseRepository
from workouttracker.routes.exercises import router as exercises_router
from workouttracker.routes.ui import mount_static
from workouttracker.routes.ui import router as ui_router
from workouttracker.routes.workouts import router as workouts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_schema(conn)
    ExerciseRepository(conn).ensure_fts()
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(
    title="Workout Tracker",
    version=settings.api_version,
    description=(
        "Workout Tracker is a strength-training API for exercise search, "
        "exercise resolution, workout sessions, set logging, RPE/RIR tracking, "
        "personal records, and progress summaries. It is designed for direct "
        "use by CLIs, mobile shortcuts, and AI agents. Agent integrations should "
        "resolve ambiguous exercise names before logging sets, use bulk logging "
        "for parsed workout text, and store exercise preferences only after the "
        "user confirms a mapping."
    ),
    openapi_tags=[
        {
            "name": "exercises",
            "description": (
                "Search, resolve, create, and manage exercises. Use "
                "`POST /exercises/resolve` before logging natural-language "
                "exercise names. If `needs_confirmation` is true, ask the user "
                "which match they meant before writing workout data."
            ),
        },
        {
            "name": "workouts",
            "description": (
                "Create workout sessions, log sets, close sessions, and review "
                "recent performance, progress, summaries, and personal records. "
                "Use bulk set logging when converting user text like "
                "`bench 135x8, 155x5` into structured data."
            ),
        },
    ],
    lifespan=lifespan,
)

_auth = [Depends(require_auth)]
app.include_router(exercises_router, dependencies=_auth)
app.include_router(workouts_router, dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}


public_dir = Path("public")
exercise_images_dir = public_dir / "exercise-images"
exercise_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/exercise-images", StaticFiles(directory=exercise_images_dir), name="exercise-images")
mount_static(app)
app.include_router(ui_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema["x-agent-guidance"] = {
        "purpose": (
            "Use this API as a durable workout memory. Let the agent handle "
            "natural language, clarification, coaching tone, reminders, and "
            "progress interpretation."
        ),
        "auth": {
            "type": "bearer",
            "note": "All endpoints except /health require Authorization: Bearer <token>.",
        },
        "recommended_workflows": [
            {
                "name": "log_sets_from_text",
                "steps": [
                    "Call POST /exercises/resolve with the user's exercise phrase.",
                    "If needs_confirmation is true, show the top alternatives and ask before logging.",
                    "Create or reuse today's workout session.",
                    "Call POST /workouts/sessions/{session_id}/sets/bulk for multiple parsed sets.",
                    "Confirm the logged sets briefly.",
                ],
            },
            {
                "name": "remember_exercise_choice",
                "steps": [
                    "Resolve the phrase and ask the user which exercise they meant.",
                    "After the user chooses, call POST /exercises/preferences.",
                    "Use the preference on future resolve calls for the same phrase.",
                ],
            },
            {
                "name": "daily_closeout",
                "steps": [
                    "Find the active or most recent session.",
                    "Call POST /workouts/sessions/{session_id}/close with notes and recovery fields if available.",
                    "Summarize total sets, notable lifts, and any personal records.",
                ],
            },
            {
                "name": "progress_review",
                "steps": [
                    "Resolve the exercise phrase.",
                    "Call /workouts/recent and /workouts/progress for the resolved exercise.",
                    "Summarize trend, best recent set, estimated 1RM, volume, and fatigue context.",
                ],
            },
        ],
        "logging_tips": [
            "Prefer structured set fields over notes when the value is known.",
            "Use rpe and rir as subjective effort signals; do not treat them as objective failure.",
            "Use set_type for warmup, working, backoff, drop, failure, and rehab sets.",
            "Do not overwrite or delete logged sets without explicit user instruction.",
            "If an exercise has image_path, render it as /exercise-images/{image_path}.",
        ],
        "skill_authoring_tips": [
            "Create a thin CLI or skill that wraps the OpenAPI operations directly.",
            "Teach the skill natural commands such as 'log this', 'start push day', 'close out lifting', and 'how is bench going'.",
            "For ambiguous phrases, call resolve first and persist user choices as preferences.",
            "Keep coaching feedback short, specific, and recovery-aware.",
        ],
        "ui": {
            "routes": ["/", "/today", "/sessions", "/exercises", "/progress", "/settings"],
            "note": "A lightweight web UI is available for human review and quick manual logging. Agents should prefer structured API operations for writes.",
        },
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
