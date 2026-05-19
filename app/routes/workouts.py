from fastapi import APIRouter, HTTPException, Request
from app.models.workout import (
    WorkoutSessionCreate, WorkoutSessionUpdate, WorkoutSessionOut,
    WorkoutSetCreate, WorkoutSetUpdate, WorkoutSetOut,
    BulkSetIn, SessionCloseIn,
)
from app.repositories.workouts import WorkoutRepository
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService
from app.services.workout_stats import WorkoutStats

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _repo(request: Request) -> WorkoutRepository:
    return WorkoutRepository(request.app.state.db)


def _ex_svc(request: Request) -> ExerciseSearchService:
    return ExerciseSearchService(ExerciseRepository(request.app.state.db))


# --- Sessions ---

@router.post("/sessions", status_code=201, response_model=WorkoutSessionOut)
def create_session(request: Request, body: WorkoutSessionCreate):
    repo = _repo(request)
    sid = repo.create_session(**body.model_dump(exclude_none=True))
    return repo.get_session(sid)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionOut)
def get_session(request: Request, session_id: int):
    s = _repo(request).get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.get("/sessions", response_model=list[WorkoutSessionOut])
def list_sessions(request: Request, start: str | None = None, end: str | None = None):
    return _repo(request).list_sessions(start=start, end=end)


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionOut)
def update_session(request: Request, session_id: int, body: WorkoutSessionUpdate):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    repo.update_session(session_id, **body.model_dump(exclude_unset=True))
    return repo.get_session(session_id)


@router.post("/sessions/{session_id}/close", response_model=WorkoutSessionOut)
def close_session(request: Request, session_id: int, body: SessionCloseIn):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    return repo.close_session(session_id, **body.model_dump(exclude_none=True))


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(request: Request, session_id: int):
    if not _repo(request).delete_session(session_id):
        raise HTTPException(404, "Session not found")


# --- Sets ---

@router.post("/sessions/{session_id}/sets", status_code=201, response_model=WorkoutSetOut)
def create_set(request: Request, session_id: int, body: WorkoutSetCreate):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    set_id = repo.create_set(session_id=session_id, **body.model_dump(exclude_none=True))
    return repo.get_set(set_id)


@router.get("/sessions/{session_id}/sets")
def list_sets(request: Request, session_id: int):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    return repo.list_sets(session_id)


@router.post("/sessions/{session_id}/sets/bulk", status_code=201,
             response_model=list[WorkoutSetOut])
def bulk_create_sets(request: Request, session_id: int, body: BulkSetIn):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    ex = _ex_svc(request).resolve(body.exercise_query)
    if not ex:
        raise HTTPException(404, f"Exercise not found: '{body.exercise_query}'")
    sets = [s.model_dump(exclude_none=True) for s in body.sets]
    ids = repo.bulk_create_sets(session_id, ex["id"], sets)
    return [repo.get_set(i) for i in ids]


@router.patch("/sets/{set_id}", response_model=WorkoutSetOut)
def update_set(request: Request, set_id: int, body: WorkoutSetUpdate):
    repo = _repo(request)
    if not repo.get_set(set_id):
        raise HTTPException(404, "Set not found")
    repo.update_set(set_id, **body.model_dump(exclude_unset=True))
    return repo.get_set(set_id)


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(request: Request, set_id: int):
    if not _repo(request).delete_set(set_id):
        raise HTTPException(404, "Set not found")


# --- History / Progress ---

@router.get("/recent")
def recent(request: Request, exercise_id: int, limit: int = 5):
    sets = _repo(request).recent_sets_for_exercise(exercise_id, limit=limit)
    return WorkoutStats().format_recent(sets, limit=limit)


@router.get("/progress")
def progress(request: Request, exercise_id: int,
             start: str | None = None, end: str | None = None):
    sets = _repo(request).progress_for_exercise(exercise_id, start=start, end=end)
    return WorkoutStats().format_progress(sets)


@router.get("/personal-records")
def personal_records(request: Request):
    return _repo(request).personal_records()


@router.get("/summary")
def summary(request: Request, start: str | None = None, end: str | None = None):
    return _repo(request).summary(start=start, end=end)
