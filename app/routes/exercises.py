import json
import sqlite3
from datetime import datetime
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Request
from app.config import settings
from app.models.exercise import (
    ExerciseCreate, ExerciseUpdate, ExerciseOut, AliasCreate, AliasOut,
    ExerciseResolveRequest, ExerciseResolveResponse,
    ExercisePreferenceCreate, ExercisePreferenceUpdate, ExercisePreferenceOut,
    ExerciseFacets,
)
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService

router = APIRouter(prefix="/exercises", tags=["exercises"])


def _repo(request: Request) -> ExerciseRepository:
    return ExerciseRepository(request.app.state.db)


def _svc(request: Request) -> ExerciseSearchService:
    return ExerciseSearchService(_repo(request))


def _with_image_urls(request: Request, exercise: dict | None) -> dict | None:
    if not exercise:
        return exercise
    base = (settings.public_base_url or str(request.base_url).rstrip("/")).rstrip("/")
    exercise["image_urls"] = [
        f"{base}/exercise-images/{quote(path, safe='/')}"
        for path in exercise.get("image_paths", [])
    ]
    return exercise


@router.get("/search", response_model=list[ExerciseOut], summary="Search exercises")
def search_exercises(request: Request, q: str = "", limit: int = 20,
                     equipment: str | None = None, muscle: str | None = None,
                     category: str | None = None, level: str | None = None,
                     mechanic: str | None = None, force: str | None = None):
    """Search by name, alias, equipment, category, or muscles."""
    filters = {
        "equipment": equipment, "muscle": muscle, "category": category,
        "level": level, "mechanic": mechanic, "force": force,
    }
    return [_with_image_urls(request, ex) for ex in _svc(request).search(q, limit=limit, **filters)]


@router.post("/resolve", response_model=ExerciseResolveResponse, summary="Resolve exercise query")
def resolve_exercise(request: Request, body: ExerciseResolveRequest):
    context = body.context.model_dump() if body.context else {}
    return _svc(request).resolve_detailed(
        body.query,
        user_id=settings.default_user_id,
        context=context,
    )


@router.get("/facets", response_model=ExerciseFacets, summary="List exercise search facets")
def exercise_facets(request: Request):
    return _repo(request).facets()


@router.get("/preferences", response_model=list[ExercisePreferenceOut],
            summary="List exercise preferences")
def list_preferences(request: Request):
    return _repo(request).list_preferences(user_id=settings.default_user_id)


@router.post("/preferences", status_code=201, response_model=ExercisePreferenceOut,
             summary="Create or update exercise preference")
def create_preference(request: Request, body: ExercisePreferenceCreate):
    repo = _repo(request)
    if not repo.get(body.preferred_exercise_id):
        raise HTTPException(404, "Exercise not found")
    pref_id = repo.upsert_preference(
        user_id=settings.default_user_id,
        phrase=body.phrase,
        preferred_exercise_id=body.preferred_exercise_id,
        context=body.context,
    )
    return repo.get_preference_by_id(pref_id)


@router.patch("/preferences/{pref_id}", response_model=ExercisePreferenceOut,
              summary="Update exercise preference")
def update_preference(request: Request, pref_id: int, body: ExercisePreferenceUpdate):
    repo = _repo(request)
    updates = body.model_dump(exclude_unset=True)
    if "preferred_exercise_id" in updates and not repo.get(updates["preferred_exercise_id"]):
        raise HTTPException(404, "Exercise not found")
    if not repo.update_preference(pref_id, **updates):
        raise HTTPException(404, "Preference not found")
    return repo.get_preference_by_id(pref_id)


@router.delete("/preferences/{pref_id}", status_code=204,
               summary="Delete exercise preference")
def delete_preference(request: Request, pref_id: int):
    if not _repo(request).delete_preference(pref_id):
        raise HTTPException(404, "Preference not found")


@router.get("/{exercise_id}", response_model=ExerciseOut, summary="Get exercise by ID")
def get_exercise(request: Request, exercise_id: int):
    ex = _repo(request).get(exercise_id)
    if not ex:
        raise HTTPException(404, "Exercise not found")
    return _with_image_urls(request, ex)


@router.post("", status_code=201, response_model=ExerciseOut, summary="Create custom exercise")
def create_exercise(request: Request, body: ExerciseCreate):
    repo = _repo(request)
    data = body.model_dump()
    for field in ("primary_muscles", "secondary_muscles", "instructions", "image_paths"):
        data[field] = json.dumps(data[field])
    eid = repo.create(**data)
    return _with_image_urls(request, repo.get(eid))


@router.patch("/{exercise_id}", response_model=ExerciseOut, summary="Update exercise")
def update_exercise(request: Request, exercise_id: int, body: ExerciseUpdate):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    updates = body.model_dump(exclude_unset=True)
    for field in ("primary_muscles", "secondary_muscles", "instructions"):
        if field in updates and updates[field] is not None:
            updates[field] = json.dumps(updates[field])
    if "image_paths" in updates and updates["image_paths"] is not None:
        updates["image_paths"] = json.dumps(updates["image_paths"])
    repo.update(exercise_id, **updates)
    return _with_image_urls(request, repo.get(exercise_id))


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
        alias_id = repo.add_alias(exercise_id, body.alias, body.source, body.confidence)
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"Alias '{body.alias}' already exists")
    normalized = body.alias.lower().strip()
    return {"id": alias_id, "exercise_template_id": exercise_id,
            "alias": normalized, "normalized_alias": normalized,
            "source": body.source, "confidence": body.confidence,
            "created_at": datetime.now()}


@router.get("/{exercise_id}/aliases", response_model=list[AliasOut],
            summary="List aliases")
def list_aliases(request: Request, exercise_id: int):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    return repo.list_aliases(exercise_id)


@router.delete("/aliases/{alias_id}", status_code=204, summary="Delete alias")
def delete_alias(request: Request, alias_id: int):
    if not _repo(request).delete_alias(alias_id):
        raise HTTPException(404, "Alias not found")
