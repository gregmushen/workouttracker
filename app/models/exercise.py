from datetime import datetime
from typing import Literal
from pydantic import BaseModel

SourceType = Literal["free_exercise_db", "custom"]


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AliasCreate(BaseModel):
    alias: str


class AliasOut(BaseModel):
    id: int
    exercise_template_id: int
    alias: str
    created_at: datetime

    model_config = {"from_attributes": True}
