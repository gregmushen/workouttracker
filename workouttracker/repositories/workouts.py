import sqlite3
from datetime import UTC, datetime


class WorkoutRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # --- Sessions ---

    def create_session(self, *, user_id: int = 1, date: str, **kwargs) -> int:
        fields = ["user_id", "date"]
        values = [user_id, date]
        optional = ["started_at", "ended_at", "title", "location", "body_weight_kg",
                    "energy_score", "soreness_score", "stress_score", "notes"]
        for f in optional:
            if f in kwargs and kwargs[f] is not None:
                fields.append(f)
                values.append(kwargs[f])
        cols = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(values))
        cur = self.conn.execute(
            f"INSERT INTO workout_sessions ({cols}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cur.lastrowid

    def get_session(self, session_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM workout_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, *, user_id: int = 1, start: str | None = None,
                      end: str | None = None) -> list[dict]:
        q = "SELECT * FROM workout_sessions WHERE user_id = ?"
        params = [user_id]
        if start:
            q += " AND date >= ?"
            params.append(start)
        if end:
            q += " AND date <= ?"
            params.append(end)
        q += " ORDER BY date DESC, id DESC"
        return [dict(r) for r in self.conn.execute(q, params).fetchall()]

    def update_session(self, session_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = [*kwargs.values(), session_id]
        self.conn.execute(
            f"UPDATE workout_sessions SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def close_session(self, session_id: int, **kwargs) -> dict | None:
        # Every other timestamp in this schema comes from SQLite's datetime('now'),
        # which is naive UTC. Take UTC explicitly, then drop the tzinfo so
        # ended_at keeps the same shape as the columns it sits beside — an
        # offset-suffixed value here would be a stored-format change, not a fix.
        updates = {"ended_at": datetime.now(UTC).replace(tzinfo=None).isoformat()}
        updates.update({k: v for k, v in kwargs.items() if v is not None})
        self.update_session(session_id, **updates)
        return self.get_session(session_id)

    def delete_session(self, session_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # --- Sets ---

    def create_set(self, *, session_id: int, exercise_template_id: int,
                   set_number: int = 1, **kwargs) -> int:
        fields = ["session_id", "exercise_template_id", "set_number"]
        values = [session_id, exercise_template_id, set_number]
        optional = ["set_type", "weight", "weight_unit", "reps", "duration_seconds",
                    "distance", "distance_unit", "rpe", "rir", "rest_seconds",
                    "avg_watts", "avg_heart_rate_bpm", "max_heart_rate_bpm",
                    "calories_kcal", "avg_cadence_rpm",
                    "notes", "performed_at"]
        for f in optional:
            if f in kwargs and kwargs[f] is not None:
                fields.append(f)
                values.append(kwargs[f])
        cols = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(values))
        cur = self.conn.execute(
            f"INSERT INTO workout_sets ({cols}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cur.lastrowid

    def get_set(self, set_id: int) -> dict | None:
        row = self.conn.execute(
            """SELECT ws.*, e.name AS exercise_name
               FROM workout_sets ws
               LEFT JOIN exercise_templates e ON e.id = ws.exercise_template_id
               WHERE ws.id = ?""",
            (set_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_sets(self, session_id: int) -> list[dict]:
        rows = self.conn.execute(
            """SELECT ws.*, e.name AS exercise_name
               FROM workout_sets ws
               LEFT JOIN exercise_templates e ON e.id = ws.exercise_template_id
               WHERE ws.session_id = ?
               ORDER BY ws.set_number, ws.id""",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_set(self, set_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = [*kwargs.values(), set_id]
        self.conn.execute(
            f"UPDATE workout_sets SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete_set(self, set_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def bulk_create_sets(self, session_id: int, exercise_template_id: int,
                         sets: list[dict]) -> list[int]:
        """Create multiple sets in one transaction. Assigns sequential set_numbers."""
        existing_count = self.conn.execute(
            """SELECT COUNT(*) FROM workout_sets
               WHERE session_id = ? AND exercise_template_id = ?""",
            (session_id, exercise_template_id),
        ).fetchone()[0]

        ids = []
        for i, s in enumerate(sets):
            set_number = existing_count + i + 1
            set_id = self.create_set(
                session_id=session_id,
                exercise_template_id=exercise_template_id,
                set_number=set_number,
                **s,
            )
            ids.append(set_id)
        return ids

    # --- History ---

    def recent_sets_for_exercise(self, exercise_template_id: int,
                                 user_id: int = 1, limit: int = 5) -> list[dict]:
        """Return last N sessions' sets for an exercise."""
        rows = self.conn.execute(
            """SELECT ws.*, s.date, s.title
               FROM workout_sets ws
               JOIN workout_sessions s ON s.id = ws.session_id
               WHERE ws.exercise_template_id = ? AND s.user_id = ?
               ORDER BY s.date DESC, s.id DESC, ws.set_number
               LIMIT ?""",
            (exercise_template_id, user_id, limit * 10),
        ).fetchall()
        return [dict(r) for r in rows]

    def progress_for_exercise(self, exercise_template_id: int, user_id: int = 1,
                               start: str | None = None, end: str | None = None) -> list[dict]:
        """Return all working sets for an exercise in date range."""
        q = """SELECT ws.*, s.date, s.title
               FROM workout_sets ws
               JOIN workout_sessions s ON s.id = ws.session_id
               WHERE ws.exercise_template_id = ? AND s.user_id = ?
               AND ws.set_type IN ('working', 'amrap', 'failure')"""
        params = [exercise_template_id, user_id]
        if start:
            q += " AND s.date >= ?"
            params.append(start)
        if end:
            q += " AND s.date <= ?"
            params.append(end)
        q += " ORDER BY s.date, s.id, ws.set_number"
        return [dict(r) for r in self.conn.execute(q, params).fetchall()]

    def personal_records(self, user_id: int = 1) -> list[dict]:
        """Best estimated 1RM per exercise (Epley: weight * (1 + reps/30))."""
        rows = self.conn.execute(
            """SELECT ws.exercise_template_id, e.name,
                      MAX(ws.weight * (1.0 + ws.reps / 30.0)) as estimated_1rm,
                      ws.weight as best_weight, ws.weight_unit, ws.reps as best_reps
               FROM workout_sets ws
               JOIN workout_sessions s ON s.id = ws.session_id
               JOIN exercise_templates e ON e.id = ws.exercise_template_id
               WHERE s.user_id = ? AND ws.weight IS NOT NULL AND ws.reps IS NOT NULL
               AND ws.set_type IN ('working', 'amrap', 'failure')
               GROUP BY ws.exercise_template_id
               ORDER BY estimated_1rm DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def summary(self, user_id: int = 1, start: str | None = None,
                end: str | None = None) -> dict:
        """High-level summary: session count, total sets, total volume."""
        q_params = [user_id]
        date_filter = ""
        if start:
            date_filter += " AND s.date >= ?"
            q_params.append(start)
        if end:
            date_filter += " AND s.date <= ?"
            q_params.append(end)

        sessions = self.conn.execute(
            f"SELECT COUNT(*) FROM workout_sessions s WHERE s.user_id = ?{date_filter}",
            q_params,
        ).fetchone()[0]

        sets_data = self.conn.execute(
            f"""SELECT COUNT(*) as total_sets,
                       SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) as total_volume
                FROM workout_sets ws
                JOIN workout_sessions s ON s.id = ws.session_id
                WHERE s.user_id = ?{date_filter}""",
            q_params,
        ).fetchone()

        return {
            "sessions": sessions,
            "total_sets": sets_data[0] or 0,
            "total_volume": round(sets_data[1] or 0, 1),
        }
