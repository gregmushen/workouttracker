class WorkoutStats:
    def format_recent(self, sets: list[dict], limit: int = 5) -> dict:
        return {"sessions": []}

    def format_progress(self, sets: list[dict]) -> dict:
        return {"sessions": [], "best_e1rm": 0, "session_count": 0}
