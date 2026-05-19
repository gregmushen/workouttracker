from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: Path = Path("data/workout.db")
    default_user_id: int = 1
    api_version: str = "0.1.0"
    bearer_token: Optional[str] = None

    model_config = {"env_prefix": "WT_"}


settings = Settings()
