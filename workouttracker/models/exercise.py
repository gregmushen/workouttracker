from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

SourceType = Literal["free_exercise_db", "custom"]
AliasSource = Literal["system", "user", "agent"]


class ExerciseCreate(BaseModel):
    source: SourceType = "custom"
    source_code: str | None = None
    name: str
    category: str | None = None
    equipment: str | None = None
    force: str | None = None
    level: str | None = None
    mechanic: str | None = None
    primary_muscles: list[str] = []
    secondary_muscles: list[str] = []
    instructions: list[str] = []
    image_paths: list[str] = []
    active: bool = True


class ExerciseUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    equipment: str | None = None
    force: str | None = None
    level: str | None = None
    mechanic: str | None = None
    primary_muscles: list[str] | None = None
    secondary_muscles: list[str] | None = None
    instructions: list[str] | None = None
    image_paths: list[str] | None = None
    active: bool | None = None


class ExerciseOut(BaseModel):
    id: int
    source: SourceType
    source_code: str | None = None
    name: str
    normalized_name: str = ""
    category: str | None = None
    equipment: str | None = None
    force: str | None = None
    level: str | None = None
    mechanic: str | None = None
    primary_muscles: list[str] = []
    secondary_muscles: list[str] = []
    instructions: list[str] = []
    image_paths: list[str] = []
    image_urls: list[str] = []
    active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AliasCreate(BaseModel):
    alias: str
    source: AliasSource = "user"
    confidence: float = 1.0


class AliasOut(BaseModel):
    id: int
    exercise_template_id: int
    alias: str
    normalized_alias: str = ""
    source: AliasSource = "user"
    confidence: float = 1.0
    created_at: datetime

    model_config = {"from_attributes": True}


class ExerciseResolveContext(BaseModel):
    equipment_available: list[str] = []
    recent_exercise_ids: list[int] = []
    session_title: str | None = None
    goal: str | None = None


class ExerciseResolveRequest(BaseModel):
    query: str
    context: ExerciseResolveContext | None = None


class ExerciseMatch(BaseModel):
    id: int
    name: str
    confidence: float
    match_reason: str


class ExerciseResolveResponse(BaseModel):
    query: str
    best_match: ExerciseMatch | None
    alternatives: list[ExerciseMatch]
    needs_confirmation: bool
    confirmation_prompt: str | None = None


class ExercisePreferenceCreate(BaseModel):
    phrase: str
    preferred_exercise_id: int
    context: dict[str, Any] = {}


class ExercisePreferenceUpdate(BaseModel):
    phrase: str | None = None
    preferred_exercise_id: int | None = None
    context: dict[str, Any] | None = None


class ExercisePreferenceOut(BaseModel):
    id: int
    user_id: int
    phrase: str
    normalized_phrase: str
    preferred_exercise_id: int
    context: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class ExerciseFacets(BaseModel):
    categories: list[str]
    equipment: list[str]
    muscles: list[str]
    levels: list[str]
    mechanics: list[str]
    forces: list[str]
