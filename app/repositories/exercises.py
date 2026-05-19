import json
import sqlite3


_FIELDS = [
    "source_code", "normalized_name", "category", "equipment", "force",
    "level", "mechanic", "primary_muscles", "secondary_muscles",
    "instructions", "image_paths",
]


def _normalize(name: str) -> str:
    return " ".join(name.lower().strip().split())


class ExerciseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_fts(self):
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS exercise_templates_fts USING fts5(
                name, normalized_name, equipment, category,
                primary_muscles, secondary_muscles,
                content='exercise_templates', content_rowid='id',
                tokenize='porter unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS ex_ai AFTER INSERT ON exercise_templates BEGIN
                INSERT INTO exercise_templates_fts(
                    rowid, name, normalized_name, equipment, category,
                    primary_muscles, secondary_muscles)
                VALUES (new.id, new.name, new.normalized_name, new.equipment,
                        new.category, new.primary_muscles, new.secondary_muscles);
            END;

            CREATE TRIGGER IF NOT EXISTS ex_ad AFTER DELETE ON exercise_templates BEGIN
                INSERT INTO exercise_templates_fts(exercise_templates_fts, rowid,
                    name, normalized_name, equipment, category,
                    primary_muscles, secondary_muscles)
                VALUES ('delete', old.id, old.name, old.normalized_name,
                        old.equipment, old.category,
                        old.primary_muscles, old.secondary_muscles);
            END;

            CREATE TRIGGER IF NOT EXISTS ex_au AFTER UPDATE ON exercise_templates BEGIN
                INSERT INTO exercise_templates_fts(exercise_templates_fts, rowid,
                    name, normalized_name, equipment, category,
                    primary_muscles, secondary_muscles)
                VALUES ('delete', old.id, old.name, old.normalized_name,
                        old.equipment, old.category,
                        old.primary_muscles, old.secondary_muscles);
                INSERT INTO exercise_templates_fts(rowid, name, normalized_name,
                    equipment, category, primary_muscles, secondary_muscles)
                VALUES (new.id, new.name, new.normalized_name, new.equipment,
                        new.category, new.primary_muscles, new.secondary_muscles);
            END;
        """)

    def _row_to_dict(self, row) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        for field in ("primary_muscles", "secondary_muscles", "instructions", "image_paths"):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
        return d

    def create(self, *, source: str, name: str, **kwargs) -> int:
        fields = ["source", "name", "normalized_name"]
        values = [source, name, _normalize(name)]
        for f in _FIELDS:
            if f in kwargs and f != "normalized_name":
                fields.append(f)
                values.append(kwargs[f])
        cols = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(values))
        cur = self.conn.execute(
            f"INSERT INTO exercise_templates ({cols}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cur.lastrowid

    def upsert(self, *, source: str, source_code: str, name: str, **kwargs) -> int:
        """Insert or update by (source, source_code). Preserves aliases."""
        existing = self.get_by_source_code(source, source_code)
        if existing:
            update_kwargs = {k: v for k, v in kwargs.items() if k != "normalized_name"}
            update_kwargs["name"] = name
            self.update(existing["id"], **update_kwargs)
            return existing["id"]
        return self.create(source=source, source_code=source_code, name=name, **kwargs)

    def get(self, exercise_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM exercise_templates WHERE id = ?", (exercise_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def get_by_source_code(self, source: str, source_code: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM exercise_templates WHERE source = ? AND source_code = ?",
            (source, source_code),
        ).fetchone()
        return self._row_to_dict(row)

    def get_by_alias(self, alias: str) -> dict | None:
        row = self.conn.execute(
            """SELECT e.* FROM exercise_templates e
               JOIN exercise_aliases a ON a.exercise_template_id = e.id
               WHERE a.alias = ?""",
            (alias.lower().strip(),),
        ).fetchone()
        return self._row_to_dict(row)

    def search_fts(self, query: str, limit: int = 20) -> list[dict]:
        fts_query = " ".join(f"{term}*" for term in query.strip().split())
        rows = self.conn.execute(
            """SELECT e.* FROM exercise_templates_fts fts
               JOIN exercise_templates e ON e.id = fts.rowid
               WHERE exercise_templates_fts MATCH ?
               ORDER BY rank LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, exercise_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        if "name" in kwargs:
            kwargs["normalized_name"] = _normalize(kwargs["name"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [exercise_id]
        self.conn.execute(
            f"UPDATE exercise_templates SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, exercise_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM exercise_templates WHERE id = ?", (exercise_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def add_alias(self, exercise_id: int, alias: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO exercise_aliases (exercise_template_id, alias) VALUES (?, ?)",
            (exercise_id, alias.lower().strip()),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_alias(self, alias_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM exercise_aliases WHERE id = ?", (alias_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def list_aliases(self, exercise_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM exercise_aliases WHERE exercise_template_id = ?",
            (exercise_id,),
        ).fetchall()
        return [dict(r) for r in rows]
