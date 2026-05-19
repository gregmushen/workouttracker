from datetime import datetime
from typing import Literal
from pydantic import BaseModel, model_validator

SetType = Literal["warmup", "working", "drop", "failure", "amrap", "bodyweight", "timed"]
WeightUnit = Literal["lb", "kg"]
DistanceUnit = Literal["m", "ft", "mi"]


# --- Session ---

class WorkoutSessionCreate(BaseModel):
    date: str
    title: str | None = None
    location: str | None = None
    started_at: str | None = None
    body_weight_kg: float | None = None
    energy_score: int | None = None
    soreness_score: int | None = None
    stress_score: int | None = None
    notes: str | None = None


class WorkoutSessionUpdate(BaseModel):
    title: str | None = None
    location: str | None = None
    body_weight_kg: float | None = None
    energy_score: int | None = None
    soreness_score: int | None = None
    stress_score: int | None = None
    notes: str | None = None


class SessionCloseIn(BaseModel):
    notes: str | None = None
    energy_score: int | None = None
    soreness_score: int | None = None
    stress_score: int | None = None


class WorkoutSessionOut(BaseModel):
    id: int
    user_id: int
    date: str
    started_at: str | None = None
    ended_at: str | None = None
    title: str | None = None
    location: str | None = None
    body_weight_kg: float | None = None
    energy_score: int | None = None
    soreness_score: int | None = None
    stress_score: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Set ---

class WorkoutSetCreate(BaseModel):
    exercise_template_id: int
    set_number: int = 1
    set_type: SetType = "working"
    weight: float | None = None
    weight_unit: WeightUnit | None = None
    reps: float | None = None
    duration_seconds: int | None = None
    distance: float | None = None
    distance_unit: DistanceUnit | None = None
    rpe: float | None = None
    rir: float | None = None
    rest_seconds: int | None = None
    notes: str | None = None
    performed_at: str | None = None

    @model_validator(mode="after")
    def check_required_fields(self):
        if self.reps is None and self.duration_seconds is None and self.distance is None:
            raise ValueError("At least one of reps, duration_seconds, or distance is required")
        if self.weight is not None and self.weight_unit is None:
            raise ValueError("weight_unit is required when weight is provided")
        return self


class WorkoutSetUpdate(BaseModel):
    set_type: SetType | None = None
    weight: float | None = None
    weight_unit: WeightUnit | None = None
    reps: float | None = None
    duration_seconds: int | None = None
    distance: float | None = None
    distance_unit: DistanceUnit | None = None
    rpe: float | None = None
    rir: float | None = None
    rest_seconds: int | None = None
    notes: str | None = None


class WorkoutSetOut(BaseModel):
    id: int
    session_id: int
    exercise_template_id: int
    set_number: int
    set_type: SetType
    weight: float | None = None
    weight_unit: WeightUnit | None = None
    reps: float | None = None
    duration_seconds: int | None = None
    distance: float | None = None
    distance_unit: DistanceUnit | None = None
    rpe: float | None = None
    rir: float | None = None
    rest_seconds: int | None = None
    notes: str | None = None
    performed_at: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Bulk set logging ---

class BulkSetItem(BaseModel):
    set_type: SetType = "working"
    weight: float | None = None
    weight_unit: WeightUnit | None = "lb"
    reps: float | None = None
    duration_seconds: int | None = None
    rpe: float | None = None
    rir: float | None = None
    notes: str | None = None


class BulkSetIn(BaseModel):
    exercise_query: str
    sets: list[BulkSetItem]
