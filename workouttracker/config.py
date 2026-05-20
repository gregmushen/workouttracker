from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: Path = Path("data/workout.db")
    default_user_id: int = 1
    api_version: str = "0.1.0"
    bearer_token: Optional[str] = None
    public_base_url: Optional[str] = None
    auto_seed_exercises: bool = True
    free_exercise_db_image_base_url: str = (
        "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises"
    )

    model_config = {"env_prefix": "WT_"}


settings = Settings()
