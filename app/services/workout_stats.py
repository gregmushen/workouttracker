from itertools import groupby


class WorkoutStats:
    def epley_1rm(self, weight: float, reps: float) -> float:
        return round(weight * (1 + reps / 30), 1)

    def top_set(self, sets: list[dict]) -> dict | None:
        working = [
            s for s in sets
            if s.get("set_type") in ("working", "amrap", "failure")
            and s.get("weight") is not None
            and s.get("reps") is not None
        ]
        if not working:
            return None
        return max(
            working,
            key=lambda s: self.epley_1rm(s["weight"], s["reps"]),
        )

    def total_volume(self, sets: list[dict]) -> float:
        return sum(
            (s.get("weight") or 0) * (s.get("reps") or 0)
            for s in sets
        )

    def format_recent(self, sets: list[dict], limit: int = 5) -> dict:
        """Group flat set rows by session, return last N sessions."""
        sessions = []
        for session_id, group in groupby(sets, key=lambda s: s["session_id"]):
            group_list = list(group)
            sessions.append({
                "session_id": session_id,
                "date": group_list[0].get("date"),
                "title": group_list[0].get("title"),
                "sets": group_list,
                "top_set": self.top_set(group_list),
                "volume": self.total_volume(group_list),
            })
            if len(sessions) >= limit:
                break
        return {"sessions": sessions}

    def format_progress(self, sets: list[dict]) -> dict:
        """Aggregate sets by session with e1RM and volume trends."""
        sessions = []
        all_e1rms = []

        for session_id, group in groupby(sets, key=lambda s: s["session_id"]):
            group_list = list(group)
            top = self.top_set(group_list)
            e1rm = self.epley_1rm(top["weight"], top["reps"]) if top else 0
            all_e1rms.append(e1rm)
            sessions.append({
                "session_id": session_id,
                "date": group_list[0].get("date"),
                "top_set": top,
                "estimated_1rm": e1rm,
                "volume": self.total_volume(group_list),
                "set_count": len(group_list),
            })

        best_e1rm = max(all_e1rms) if all_e1rms else 0
        return {
            "sessions": sessions,
            "best_e1rm": best_e1rm,
            "session_count": len(sessions),
        }
