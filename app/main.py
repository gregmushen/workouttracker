from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from app.auth import require_auth
from app.config import settings
from app.database import get_connection, init_schema
from app.repositories.exercises import ExerciseRepository
from app.routes.exercises import router as exercises_router
from app.routes.workouts import router as workouts_router


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
    lifespan=lifespan,
)

_auth = [Depends(require_auth)]
app.include_router(exercises_router, dependencies=_auth)
app.include_router(workouts_router, dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}
