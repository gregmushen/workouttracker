import json
from fastapi import APIRouter, HTTPException, Request
from app.models.exercise import ExerciseCreate, ExerciseUpdate, ExerciseOut, AliasCreate, AliasOut
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService

router = APIRouter(prefix="/exercises", tags=["exercises"])


def _repo(request: Request) -> ExerciseRepository:
    return ExerciseRepository(request.app.state.db)


def _svc(request: Request) -> ExerciseSearchService:
    return ExerciseSearchService(_repo(request))


@router.get("/search", response_model=list[ExerciseOut], summary="Search exercises")
def search_exercises(request: Request, q: str, limit: int = 20):
    """Search by name, alias, equipment, category, or muscles."""
    return _svc(request).search(q, limit=limit)


@router.get("/{exercise_id}", response_model=ExerciseOut, summary="Get exercise by ID")
def get_exercise(request: Request, exercise_id: int):
    ex = _repo(request).get(exercise_id)
    if not ex:
        raise HTTPException(404, "Exercise not found")
    return ex


@router.post("", status_code=201, response_model=ExerciseOut, summary="Create custom exercise")
def create_exercise(request: Request, body: ExerciseCreate):
    repo = _repo(request)
    data = body.model_dump()
    for field in ("primary_muscles", "secondary_muscles", "instructions", "image_paths"):
        data[field] = json.dumps(data[field])
    eid = repo.create(**data)
    return repo.get(eid)


@router.patch("/{exercise_id}", response_model=ExerciseOut, summary="Update exercise")
def update_exercise(request: Request, exercise_id: int, body: ExerciseUpdate):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    updates = body.model_dump(exclude_unset=True)
    for field in ("primary_muscles", "secondary_muscles", "instructions"):
        if field in updates and updates[field] is not None:
            updates[field] = json.dumps(updates[field])
    repo.update(exercise_id, **updates)
    return repo.get(exercise_id)


@router.delete("/{exercise_id}", status_code=204, summary="Delete exercise")
def delete_exercise(request: Request, exercise_id: int):
    if not _repo(request).delete(exercise_id):
        raise HTTPException(404, "Exercise not found")


@router.post("/{exercise_id}/aliases", status_code=201, response_model=AliasOut,
             summary="Add alias")
def add_alias(request: Request, exercise_id: int, body: AliasCreate):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    try:
        alias_id = repo.add_alias(exercise_id, body.alias)
    except Exception:
        raise HTTPException(409, f"Alias '{body.alias}' already exists")
    import datetime
    return {"id": alias_id, "exercise_template_id": exercise_id,
            "alias": body.alias.lower().strip(), "created_at": datetime.datetime.now()}


@router.delete("/aliases/{alias_id}", status_code=204, summary="Delete alias")
def delete_alias(request: Request, alias_id: int):
    if not _repo(request).delete_alias(alias_id):
        raise HTTPException(404, "Alias not found")
