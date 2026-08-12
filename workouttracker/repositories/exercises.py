import json
import sqlite3


_FIELDS = [
    "source_code", "normalized_name", "category", "equipment", "force",
    "level", "mechanic", "primary_muscles", "secondary_muscles",
    "instructions", "image_paths", "active",
]


def _normalize(name: str) -> str:
    return " ".join(name.lower().strip().split())


def _fts_prefix_query(query: str) -> str:
    """Build a prefix MATCH expression, dropping characters FTS5 treats as syntax.

    Punctuation left in a term ("Bicycling,*") is an FTS5 syntax error, which the
    caller would swallow into an empty result — so a name like
    "Bicycling, Stationary" could never find itself. Terms are reduced to
    alphanumerics; a query with nothing left yields "" so the caller can skip
    the query entirely rather than send a malformed one.
    """
    terms = []
    for raw in query.split():
        term = "".join(ch for ch in raw if ch.isalnum())
        if term:
            terms.append(f"{term}*")
    return " ".join(terms)


class ExerciseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM exercise_templates").fetchone()[0]

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
        if "active" in d:
            d["active"] = bool(d["active"])
        return d

    def _preference_to_dict(self, row) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        try:
            d["context"] = json.loads(d.get("context") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["context"] = {}
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
            "SELECT * FROM exercise_templates WHERE id = ? AND active = 1", (exercise_id,)
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
               WHERE a.normalized_alias = ? AND e.active = 1
               ORDER BY CASE a.source WHEN 'user' THEN 0 WHEN 'agent' THEN 1 ELSE 2 END,
                        a.confidence DESC
               LIMIT 1""",
            (_normalize(alias),),
        ).fetchone()
        return self._row_to_dict(row)

    def get_by_normalized_name(self, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM exercise_templates WHERE normalized_name = ? AND active = 1 LIMIT 1",
            (_normalize(name),),
        ).fetchone()
        return self._row_to_dict(row)

    def search_fts(self, query: str, limit: int = 20, offset: int = 0, **filters) -> list[dict]:
        fts_query = _fts_prefix_query(query)
        if not fts_query:
            return []
        where = ["exercise_templates_fts MATCH ?", "e.active = 1"]
        values = [fts_query]
        for field in ("equipment", "category", "level", "mechanic", "force"):
            if filters.get(field):
                where.append(f"lower(e.{field}) = lower(?)")
                values.append(filters[field])
        if filters.get("muscle"):
            where.append("(lower(e.primary_muscles) LIKE lower(?) OR lower(e.secondary_muscles) LIKE lower(?))")
            muscle = f"%{filters['muscle']}%"
            values.extend([muscle, muscle])
        values.extend([limit, offset])
        try:
            rows = self.conn.execute(
                """SELECT e.* FROM exercise_templates_fts fts
                   JOIN exercise_templates e ON e.id = fts.rowid
                   WHERE """ + " AND ".join(where) + """
                   ORDER BY rank LIMIT ? OFFSET ?""",
                values,
            ).fetchall()
        except Exception:
            return []
        return [self._row_to_dict(r) for r in rows]

    def list_filtered(self, limit: int = 20, offset: int = 0, **filters) -> list[dict]:
        where = ["active = 1"]
        values = []
        for field in ("equipment", "category", "level", "mechanic", "force"):
            if filters.get(field):
                where.append(f"lower({field}) = lower(?)")
                values.append(filters[field])
        if filters.get("muscle"):
            where.append("(lower(primary_muscles) LIKE lower(?) OR lower(secondary_muscles) LIKE lower(?))")
            muscle = f"%{filters['muscle']}%"
            values.extend([muscle, muscle])
        values.extend([limit, offset])
        rows = self.conn.execute(
            "SELECT * FROM exercise_templates WHERE " + " AND ".join(where) + " ORDER BY name LIMIT ? OFFSET ?",
            values,
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
            "UPDATE exercise_templates SET active = 0, updated_at = datetime('now') WHERE id = ?",
            (exercise_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def add_alias(self, exercise_id: int, alias: str, source: str = "user",
                  confidence: float = 1.0) -> int:
        normalized = _normalize(alias)
        cur = self.conn.execute(
            """INSERT INTO exercise_aliases
               (exercise_template_id, alias, normalized_alias, source, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (exercise_id, normalized, normalized, source, confidence),
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

    def get_preference(self, *, user_id: int, phrase: str) -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM exercise_preferences
               WHERE user_id = ? AND normalized_phrase = ?""",
            (user_id, _normalize(phrase)),
        ).fetchone()
        return self._preference_to_dict(row)

    def list_preferences(self, *, user_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM exercise_preferences WHERE user_id = ? ORDER BY phrase",
            (user_id,),
        ).fetchall()
        return [self._preference_to_dict(r) for r in rows]

    def upsert_preference(self, *, user_id: int, phrase: str,
                          preferred_exercise_id: int, context: dict | None = None) -> int:
        normalized = _normalize(phrase)
        self.conn.execute(
            """INSERT INTO exercise_preferences
               (user_id, phrase, normalized_phrase, preferred_exercise_id, context)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, normalized_phrase) DO UPDATE SET
                   phrase = excluded.phrase,
                   preferred_exercise_id = excluded.preferred_exercise_id,
                   context = excluded.context,
                   updated_at = datetime('now')""",
            (user_id, phrase, normalized, preferred_exercise_id, json.dumps(context or {})),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM exercise_preferences WHERE user_id = ? AND normalized_phrase = ?",
            (user_id, normalized),
        ).fetchone()
        return row["id"]

    def update_preference(self, pref_id: int, **updates) -> bool:
        if not updates:
            return self.get_preference_by_id(pref_id) is not None
        if "phrase" in updates:
            updates["normalized_phrase"] = _normalize(updates["phrase"])
        if "context" in updates and isinstance(updates["context"], dict):
            updates["context"] = json.dumps(updates["context"])
        sets = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [pref_id]
        cur = self.conn.execute(
            f"UPDATE exercise_preferences SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_preference_by_id(self, pref_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM exercise_preferences WHERE id = ?", (pref_id,)
        ).fetchone()
        return self._preference_to_dict(row)

    def delete_preference(self, pref_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM exercise_preferences WHERE id = ?", (pref_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def facets(self) -> dict:
        def values_for(column: str) -> list[str]:
            rows = self.conn.execute(
                f"""SELECT DISTINCT {column} value FROM exercise_templates
                    WHERE active = 1 AND {column} IS NOT NULL AND {column} != ''
                    ORDER BY {column}"""
            ).fetchall()
            return [r["value"] for r in rows]

        muscles = set()
        rows = self.conn.execute(
            """SELECT primary_muscles, secondary_muscles FROM exercise_templates
               WHERE active = 1"""
        ).fetchall()
        for row in rows:
            for field in ("primary_muscles", "secondary_muscles"):
                try:
                    muscles.update(json.loads(row[field] or "[]"))
                except (json.JSONDecodeError, TypeError):
                    pass

        return {
            "categories": values_for("category"),
            "equipment": values_for("equipment"),
            "muscles": sorted(m for m in muscles if m),
            "levels": values_for("level"),
            "mechanics": values_for("mechanic"),
            "forces": values_for("force"),
        }

    def log_search(self, *, user_id: int, query: str, matched_exercise_id: int | None,
                   confidence: float | None, required_confirmation: bool) -> None:
        self.conn.execute(
            """INSERT INTO exercise_search_logs
               (user_id, query, matched_exercise_id, confidence, required_confirmation)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, query, matched_exercise_id, confidence, int(required_confirmation)),
        )
        self.conn.commit()
