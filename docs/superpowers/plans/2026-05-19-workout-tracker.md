# Workout Tracker API — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI + SQLite workout tracking API with exercise search, session/set logging, bulk set input, history, and e1RM-based progress — deployed to garageband via Kamal behind a Cloudflare tunnel at `wt.paracosmlab.com`.

**Architecture:** Mirrors the nutrition tracker exactly: raw SQLite via `sqlite3`, repository pattern for DB access, Pydantic models for I/O, FTS5 for exercise search. All tables created in `init_schema`; alembic handles future migrations.

**Tech Stack:** Python 3.12, FastAPI, SQLite (WAL + FTS5), Pydantic v2, pydantic-settings, hatchling, Kamal 2, Woodpecker CI, Cloudflare tunnel, Docker (python:3.12-slim), pytest.

---

## File Map

```
workouttracker/
├── app/
│   ├── __init__.py
│   ├── auth.py                        # Bearer token auth (identical to nutrition tracker)
│   ├── config.py                      # Settings with WT_ env prefix
│   ├── database.py                    # init_schema: all 4 tables + indexes
│   ├── main.py                        # FastAPI app, lifespan, routers, /health
│   ├── models/
│   │   ├── __init__.py
│   │   ├── exercise.py                # ExerciseTemplateOut, ExerciseCreate, AliasCreate
│   │   └── workout.py                 # WorkoutSessionOut, WorkoutSetOut, BulkSetIn
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── exercises.py               # ExerciseRepository: CRUD + FTS + aliases
│   │   └── workouts.py                # WorkoutRepository: sessions + sets + history
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── exercises.py               # /exercises/* endpoints
│   │   └── workouts.py                # /workouts/* endpoints
│   └── services/
│       ├── __init__.py
│       ├── exercise_search.py         # Alias-first, then FTS fallback
│       └── workout_stats.py           # Epley e1RM, volume, progress aggregation
├── scripts/
│   ├── __init__.py
│   └── import_exercises.py            # Bulk import from free-exercise-db JSON
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # in-memory db + TestClient fixtures
│   ├── test_health.py
│   ├── test_exercise_repository.py
│   ├── test_exercise_search.py
│   ├── test_routes_exercises.py
│   ├── test_workout_stats.py
│   ├── test_routes_workouts.py
│   └── test_import_exercises.py
├── bin/
│   └── import-exercises               # Shell wrapper for import script
├── alembic/
│   ├── env.py
│   └── versions/0001_initial_schema.py
├── config/
│   └── deploy.yml                     # Kamal deploy config
├── docs/superpowers/specs/...         # existing
├── .woodpecker.yml
├── alembic.ini
├── Dockerfile
├── entrypoint.sh
├── pyproject.toml
└── README.md
```

---

## Task 1: Repo Scaffold + CI/Deploy Infrastructure

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `Dockerfile`
- Create: `entrypoint.sh`
- Create: `.woodpecker.yml`
- Create: `config/deploy.yml`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_initial_schema.py`
- Create: all `__init__.py` files

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "workouttracker"
version = "0.1.0"
description = "Open-source workout/lifting tracker REST API"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "alembic>=1.13",
    "sqlalchemy>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
    "ruff>=0.4",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2: Create `README.md`**

```markdown
# Workout Tracker

A personal lifting and workout tracking API built with FastAPI and SQLite.

**Live:** https://wt.paracosmlab.com — OpenAPI schema at `/openapi.json`
```

- [ ] **Step 3: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
```

- [ ] **Step 4: Create `entrypoint.sh`**

```sh
#!/bin/sh
set -e

DB_PATH="${WT_DB_PATH:-data/workout.db}"
mkdir -p "$(dirname "$DB_PATH")"

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 5: Create `.woodpecker.yml`**

```yaml
steps:
  lint:
    image: python:3.12-slim
    commands:
      - pip install ruff
      - ruff check app/ tests/ scripts/
    when:
      event: [push, pull_request, manual, tag]

  secret-scan:
    image: zricethezav/gitleaks:latest
    commands:
      - gitleaks detect --source . --verbose --no-banner
    when:
      event: [push, pull_request, manual, tag]

  test:
    image: python:3.12-slim
    commands:
      - pip install -e ".[dev]"
      - pytest tests/ --tb=short -q
    depends_on:
      - lint
      - secret-scan
    when:
      event: [push, pull_request, manual, tag]

  deploy:
    image: ruby:3.3-alpine
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    commands:
      - apk add --no-cache openssh-client curl git docker-cli docker-cli-buildx build-base
      - gem install kamal --no-document -q
      - mkdir -p ~/.ssh
      - echo "$DEPLOY_SSH_KEY" > ~/.ssh/stupidclaw_garageband_ed25519
      - chmod 600 ~/.ssh/stupidclaw_garageband_ed25519
      - printf "Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile /dev/null\n" > ~/.ssh/config
      - printf "WT_BEARER_TOKEN=%s\nTUNNEL_TOKEN=%s\nKAMAL_REGISTRY_PASSWORD=%s\n" "$WT_BEARER_TOKEN" "$CLOUDFLARE_TUNNEL_TOKEN" "$KAMAL_REGISTRY_PASSWORD" > .kamal/secrets
      - kamal deploy
      - kamal accessory boot cloudflared 2>/dev/null || kamal accessory reboot cloudflared
    environment:
      DEPLOY_SSH_KEY:
        from_secret: deploy_ssh_key
      WT_BEARER_TOKEN:
        from_secret: WT_BEARER_TOKEN
      CLOUDFLARE_TUNNEL_TOKEN:
        from_secret: CLOUDFLARE_TUNNEL_TOKEN
      KAMAL_REGISTRY_PASSWORD:
        from_secret: KAMAL_REGISTRY_PASSWORD
    depends_on:
      - test
    when:
      branch: master
      event: push
```

- [ ] **Step 6: Create `config/deploy.yml`**

```yaml
service: workouttracker
image: workouttracker

servers:
  web:
    - 192.168.1.76

registry:
  server: 192.168.1.76:5000
  username: kamal
  password:
    - KAMAL_REGISTRY_PASSWORD

env:
  clear:
    WT_DB_PATH: /data/workout.db
  secret:
    - WT_BEARER_TOKEN

volumes:
  - workouttracker_data:/data

proxy:
  host: wt.paracosmlab.com
  app_port: 8000
  healthcheck:
    path: /health
    interval: 5
    timeout: 10

builder:
  arch: amd64
  remote: ssh://gregmushen@192.168.1.76

ssh:
  user: gregmushen
  keys:
    - ~/.ssh/stupidclaw_garageband_ed25519

accessories:
  cloudflared:
    image: cloudflare/cloudflared:latest
    host: 192.168.1.76
    cmd: tunnel --no-autoupdate run
    env:
      secret:
        - TUNNEL_TOKEN

aliases:
  shell: app exec --interactive --reuse "sh"
  logs: app logs -f
```

> **Note:** Before the first deploy, create a new Cloudflare tunnel for `wt.paracosmlab.com` and add its token as the `CLOUDFLARE_TUNNEL_TOKEN` Woodpecker secret. Add a CNAME `wt` → the tunnel's `.cfargotunnel.com` address. Set the tunnel ingress to `http://kamal-proxy:80`. Also create a `.kamal/` dir with empty `secrets` file (gitignored) and add Woodpecker secrets: `deploy_ssh_key`, `WT_BEARER_TOKEN`, `CLOUDFLARE_TUNNEL_TOKEN`, `KAMAL_REGISTRY_PASSWORD`.

- [ ] **Step 7: Create `alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///data/workout.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 8: Create `alembic/env.py`**

```python
from logging.config import fileConfig
from pathlib import Path
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    import sqlite3
    from pathlib import Path
    from app.config import settings

    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connectable = sqlite3.connect(str(db_path))

    with context.begin_transaction():
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 9: Create `alembic/versions/0001_initial_schema.py`**

```python
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Schema is created by app/database.py init_schema on startup.
    # This migration just marks the initial state.
    pass


def downgrade():
    pass
```

- [ ] **Step 10: Create all `__init__.py` files**

```bash
mkdir -p app/models app/repositories app/routes app/services scripts tests bin config .kamal
touch app/__init__.py app/models/__init__.py app/repositories/__init__.py
touch app/routes/__init__.py app/services/__init__.py
touch scripts/__init__.py tests/__init__.py
touch .kamal/secrets
echo ".kamal/secrets" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".venv/" >> .gitignore
echo "*.db" >> .gitignore
```

- [ ] **Step 11: Initialize git and push to GitHub**

```bash
git init
git add .
git commit -m "chore: initial project scaffold"
# Create repo at github.com/gregmushen/workouttracker, then:
git remote add origin https://github.com/gregmushen/workouttracker.git
git push -u origin master
```

---

## Task 2: Database Schema

**Files:**
- Create: `app/database.py`

- [ ] **Step 1: Write `app/database.py`**

```python
import sqlite3
from pathlib import Path
from app.config import settings


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercise_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'custom'
                CHECK(source IN ('free_exercise_db', 'custom')),
            source_code TEXT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL DEFAULT '',
            category TEXT,
            equipment TEXT,
            force TEXT,
            level TEXT,
            mechanic TEXT,
            primary_muscles TEXT NOT NULL DEFAULT '[]',
            secondary_muscles TEXT NOT NULL DEFAULT '[]',
            instructions TEXT NOT NULL DEFAULT '[]',
            image_paths TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS exercise_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_template_id INTEGER NOT NULL
                REFERENCES exercise_templates(id) ON DELETE CASCADE,
            alias TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(alias)
        );

        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            title TEXT,
            location TEXT,
            body_weight_kg REAL,
            energy_score INTEGER,
            soreness_score INTEGER,
            stress_score INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL
                REFERENCES workout_sessions(id) ON DELETE CASCADE,
            exercise_template_id INTEGER NOT NULL
                REFERENCES exercise_templates(id),
            set_number INTEGER NOT NULL DEFAULT 1,
            set_type TEXT NOT NULL DEFAULT 'working'
                CHECK(set_type IN ('warmup','working','drop','failure','amrap','bodyweight','timed')),
            weight REAL,
            weight_unit TEXT CHECK(weight_unit IN ('lb','kg')),
            reps REAL,
            duration_seconds INTEGER,
            distance REAL,
            distance_unit TEXT CHECK(distance_unit IN ('m','ft','mi')),
            rpe REAL,
            rir REAL,
            rest_seconds INTEGER,
            notes TEXT,
            performed_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_source_code
            ON exercise_templates(source, source_code) WHERE source_code IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_exercise_name
            ON exercise_templates(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_date
            ON workout_sessions(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_sets_session
            ON workout_sets(session_id);
        CREATE INDEX IF NOT EXISTS idx_sets_exercise
            ON workout_sets(exercise_template_id);
    """)
```

- [ ] **Step 2: Commit**

```bash
git add app/database.py
git commit -m "feat: database schema — exercise_templates, aliases, sessions, sets"
```

---

## Task 3: App Skeleton + Health Test

**Files:**
- Create: `app/config.py`
- Create: `app/auth.py`
- Create: `app/main.py`
- Create: `tests/conftest.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write failing health test**

```python
# tests/test_health.py
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pip install -e ".[dev]"
pytest tests/test_health.py -v
```

Expected: FAIL (no module `app.main`)

- [ ] **Step 3: Write `app/config.py`**

```python
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
```

- [ ] **Step 4: Write `app/auth.py`**

```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    if not settings.bearer_token:
        return
    if credentials is None or credentials.credentials != settings.bearer_token:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")
```

- [ ] **Step 5: Write `app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from app.auth import require_auth
from app.config import settings
from app.database import get_connection, init_schema
from app.repositories.exercises import ExerciseRepository
from app.routes.exercises import router as exercises_router
from app.routes.workouts import router as workouts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_schema(conn)
    ExerciseRepository(conn).ensure_fts()
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(
    title="Workout Tracker",
    version=settings.api_version,
    lifespan=lifespan,
)

_auth = [Depends(require_auth)]
app.include_router(exercises_router, dependencies=_auth)
app.include_router(workouts_router, dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.api_version}
```

- [ ] **Step 6: Write `tests/conftest.py`**

```python
import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_schema


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("app.main.get_connection", lambda *args, **kwargs: db)
    with TestClient(app) as c:
        yield c
```

Note: `app/routes/exercises.py` and `app/routes/workouts.py` are imported by `main.py` but don't exist yet — create empty router stubs:

```python
# app/routes/exercises.py  (stub — replace in Task 5)
from fastapi import APIRouter
router = APIRouter(prefix="/exercises", tags=["exercises"])
```

```python
# app/routes/workouts.py  (stub — replace in Task 9)
from fastapi import APIRouter
router = APIRouter(prefix="/workouts", tags=["workouts"])
```

And empty `app/repositories/exercises.py` stub:

```python
# app/repositories/exercises.py  (stub — replace in Task 4)
import sqlite3

class ExerciseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_fts(self):
        pass
```

- [ ] **Step 7: Run health test — verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add app/ tests/
git commit -m "feat: app skeleton — config, auth, main, health endpoint"
```

---

## Task 4: Exercise Repository + FTS

**Files:**
- Create: `app/repositories/exercises.py` (replace stub)
- Create: `tests/test_exercise_repository.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_exercise_repository.py
import pytest
from app.repositories.exercises import ExerciseRepository


def _repo(db):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo


def test_create_and_get(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Barbell Bench Press",
                      equipment="barbell", category="strength",
                      primary_muscles='["chest","triceps"]')
    ex = repo.get(eid)
    assert ex["name"] == "Barbell Bench Press"
    assert ex["equipment"] == "barbell"


def test_search_fts_by_name(db):
    repo = _repo(db)
    repo.create(source="custom", name="Barbell Squat", equipment="barbell", category="strength")
    repo.create(source="custom", name="Leg Press", equipment="machine", category="strength")
    results = repo.search_fts("squat")
    assert len(results) == 1
    assert results[0]["name"] == "Barbell Squat"


def test_upsert_by_source_code(db):
    repo = _repo(db)
    repo.upsert(source="free_exercise_db", source_code="bench_press",
                name="Bench Press", equipment="barbell", category="strength")
    repo.upsert(source="free_exercise_db", source_code="bench_press",
                name="Bench Press (updated)", equipment="barbell", category="strength")
    results = repo.search_fts("bench")
    assert len(results) == 1
    assert results[0]["name"] == "Bench Press (updated)"


def test_add_and_get_alias(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Barbell Bench Press",
                      equipment="barbell", category="strength")
    repo.add_alias(eid, "bench")
    result = repo.get_by_alias("bench")
    assert result["id"] == eid


def test_delete_alias(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Squat", equipment="barbell", category="strength")
    alias_id = repo.add_alias(eid, "sq")
    repo.delete_alias(alias_id)
    assert repo.get_by_alias("sq") is None


def test_list_aliases(db):
    repo = _repo(db)
    eid = repo.create(source="custom", name="Deadlift", equipment="barbell", category="strength")
    repo.add_alias(eid, "dl")
    repo.add_alias(eid, "deadlift")
    aliases = repo.list_aliases(eid)
    assert len(aliases) == 2
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_exercise_repository.py -v
```

Expected: FAIL (ExerciseRepository missing methods)

- [ ] **Step 3: Write `app/repositories/exercises.py`**

```python
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
        """Insert or replace by (source, source_code). Preserves aliases."""
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_exercise_repository.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/repositories/exercises.py tests/test_exercise_repository.py
git commit -m "feat: ExerciseRepository — CRUD, FTS5 search, aliases"
```

---

## Task 5: Exercise Search Service + Routes

**Files:**
- Create: `app/services/exercise_search.py`
- Create: `app/models/exercise.py`
- Create: `app/routes/exercises.py` (replace stub)
- Create: `tests/test_exercise_search.py`
- Create: `tests/test_routes_exercises.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_exercise_search.py
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService


def _seed(db, name, **kwargs):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, **kwargs)


def test_search_falls_back_to_fts(db):
    eid = _seed(db, "Barbell Bench Press", equipment="barbell")
    svc = ExerciseSearchService(ExerciseRepository(db))
    results = svc.search("bench")
    assert len(results) >= 1
    assert any(r["id"] == eid for r in results)


def test_alias_takes_priority(db):
    eid1 = _seed(db, "Barbell Bench Press", equipment="barbell")
    eid2 = _seed(db, "Bench Something Else", equipment="dumbbell")
    repo = ExerciseRepository(db)
    repo.add_alias(eid1, "bench")
    svc = ExerciseSearchService(repo)
    results = svc.search("bench")
    assert results[0]["id"] == eid1


def test_resolve_returns_single(db):
    eid = _seed(db, "Overhead Press", equipment="barbell")
    repo = ExerciseRepository(db)
    repo.add_alias(eid, "ohp")
    svc = ExerciseSearchService(repo)
    ex = svc.resolve("ohp")
    assert ex["id"] == eid


def test_resolve_returns_none_for_unknown(db):
    svc = ExerciseSearchService(ExerciseRepository(db))
    assert svc.resolve("xyzzy") is None
```

```python
# tests/test_routes_exercises.py
from app.repositories.exercises import ExerciseRepository


def _seed(db, name="Bench Press", **kwargs):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name,
                       equipment="barbell", category="strength", **kwargs)


def test_search_exercises(client, db):
    _seed(db, "Barbell Squat")
    _seed(db, "Leg Press")
    r = client.get("/exercises/search?q=squat")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Barbell Squat"


def test_get_exercise(client, db):
    eid = _seed(db)
    r = client.get(f"/exercises/{eid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Bench Press"


def test_get_exercise_404(client):
    r = client.get("/exercises/9999")
    assert r.status_code == 404


def test_create_exercise(client, db):
    ExerciseRepository(db).ensure_fts()
    r = client.post("/exercises", json={
        "name": "Custom Row",
        "source": "custom",
        "equipment": "barbell",
        "category": "strength",
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Custom Row"


def test_update_exercise(client, db):
    eid = _seed(db)
    r = client.patch(f"/exercises/{eid}", json={"equipment": "dumbbell"})
    assert r.status_code == 200
    assert r.json()["equipment"] == "dumbbell"


def test_delete_exercise(client, db):
    eid = _seed(db)
    r = client.delete(f"/exercises/{eid}")
    assert r.status_code == 204


def test_add_alias(client, db):
    eid = _seed(db, "Overhead Press")
    r = client.post(f"/exercises/{eid}/aliases", json={"alias": "ohp"})
    assert r.status_code == 201
    assert r.json()["alias"] == "ohp"


def test_delete_alias(client, db):
    eid = _seed(db)
    repo = ExerciseRepository(db)
    aid = repo.add_alias(eid, "bench")
    r = client.delete(f"/exercises/aliases/{aid}")
    assert r.status_code == 204
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_exercise_search.py tests/test_routes_exercises.py -v
```

- [ ] **Step 3: Write `app/services/exercise_search.py`**

```python
from app.repositories.exercises import ExerciseRepository


class ExerciseSearchService:
    def __init__(self, repo: ExerciseRepository):
        self.repo = repo

    def search(self, query: str, limit: int = 20) -> list[dict]:
        alias_match = self.repo.get_by_alias(query.strip())
        if alias_match:
            return [alias_match]
        return self.repo.search_fts(query, limit=limit)

    def resolve(self, query: str) -> dict | None:
        """Return single best match for a query (for bulk set logging)."""
        results = self.search(query, limit=1)
        return results[0] if results else None
```

- [ ] **Step 4: Write `app/models/exercise.py`**

```python
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
```

- [ ] **Step 5: Write `app/routes/exercises.py`**

```python
import json
from fastapi import APIRouter, HTTPException, Request
from app.models.exercise import ExerciseCreate, ExerciseUpdate, ExerciseOut, AliasCreate, AliasOut
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService

router = APIRouter(prefix="/exercises", tags=["exercises"])


def _repo(request: Request) -> ExerciseRepository:
    return ExerciseRepository(request.app.state.db)


def _svc(request: Request) -> ExerciseSearchService:
    return ExerciseSearchService(_repo(request))


def _serialize(data: list[dict] | dict) -> list[dict] | dict:
    """Ensure JSON fields are deserialized for Pydantic validation."""
    return data


@router.get("/search", response_model=list[ExerciseOut], summary="Search exercises")
def search_exercises(request: Request, q: str, limit: int = 20):
    """Search by name, alias, equipment, category, or muscles."""
    return _svc(request).search(q, limit=limit)


@router.get("/{exercise_id}", response_model=ExerciseOut, summary="Get exercise by ID")
def get_exercise(request: Request, exercise_id: int):
    ex = _repo(request).get(exercise_id)
    if not ex:
        raise HTTPException(404, "Exercise not found")
    return ex


@router.post("", status_code=201, response_model=ExerciseOut, summary="Create custom exercise")
def create_exercise(request: Request, body: ExerciseCreate):
    repo = _repo(request)
    data = body.model_dump()
    # Serialize list fields to JSON strings for storage
    for field in ("primary_muscles", "secondary_muscles", "instructions", "image_paths"):
        data[field] = json.dumps(data[field])
    eid = repo.create(**data)
    return repo.get(eid)


@router.patch("/{exercise_id}", response_model=ExerciseOut, summary="Update exercise")
def update_exercise(request: Request, exercise_id: int, body: ExerciseUpdate):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    updates = body.model_dump(exclude_unset=True)
    for field in ("primary_muscles", "secondary_muscles", "instructions"):
        if field in updates and updates[field] is not None:
            updates[field] = json.dumps(updates[field])
    repo.update(exercise_id, **updates)
    return repo.get(exercise_id)


@router.delete("/{exercise_id}", status_code=204, summary="Delete exercise")
def delete_exercise(request: Request, exercise_id: int):
    if not _repo(request).delete(exercise_id):
        raise HTTPException(404, "Exercise not found")


@router.post("/{exercise_id}/aliases", status_code=201, response_model=AliasOut,
             summary="Add alias")
def add_alias(request: Request, exercise_id: int, body: AliasCreate):
    repo = _repo(request)
    if not repo.get(exercise_id):
        raise HTTPException(404, "Exercise not found")
    try:
        alias_id = repo.add_alias(exercise_id, body.alias)
    except Exception:
        raise HTTPException(409, f"Alias '{body.alias}' already exists")
    return {"id": alias_id, "exercise_template_id": exercise_id,
            "alias": body.alias.lower().strip(), "created_at": __import__("datetime").datetime.now()}


@router.delete("/aliases/{alias_id}", status_code=204, summary="Delete alias")
def delete_alias(request: Request, alias_id: int):
    if not _repo(request).delete_alias(alias_id):
        raise HTTPException(404, "Alias not found")
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/test_exercise_search.py tests/test_routes_exercises.py -v
```

Expected: all PASS

- [ ] **Step 7: Run full suite**

```bash
pytest tests/ --tb=short -q
```

- [ ] **Step 8: Commit**

```bash
git add app/ tests/
git commit -m "feat: exercise search service and CRUD routes"
```

---

## Task 6: Exercise Import Script

**Files:**
- Create: `scripts/import_exercises.py`
- Create: `bin/import-exercises`
- Create: `tests/test_import_exercises.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_import_exercises.py
import json
import tempfile
import os
from scripts.import_exercises import import_exercises
from app.database import get_connection, init_schema
from app.repositories.exercises import ExerciseRepository

SAMPLE = [
    {
        "id": "Barbell_Bench_Press_-_Medium_Grip",
        "name": "Barbell Bench Press - Medium Grip",
        "force": "push",
        "level": "beginner",
        "mechanic": "compound",
        "equipment": "barbell",
        "primaryMuscles": ["chest"],
        "secondaryMuscles": ["shoulders", "triceps"],
        "instructions": ["Lie on bench", "Lower bar to chest"],
        "category": "strength",
        "images": [],
    },
    {
        "id": "Squat",
        "name": "Barbell Squat",
        "force": "push",
        "level": "intermediate",
        "mechanic": "compound",
        "equipment": "barbell",
        "primaryMuscles": ["quadriceps"],
        "secondaryMuscles": ["glutes"],
        "instructions": ["Stand with bar on upper back"],
        "category": "strength",
        "images": [],
    },
]


def test_import_creates_exercises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE, f)
        path = f.name
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as dbf:
            db_path = dbf.name
        import_exercises(path, db_path)
        conn = get_connection(__import__("pathlib").Path(db_path))
        repo = ExerciseRepository(conn)
        results = repo.search_fts("bench")
        assert len(results) == 1
        assert results[0]["equipment"] == "barbell"
        assert results[0]["source"] == "free_exercise_db"
        conn.close()
    finally:
        os.unlink(path)
        os.unlink(db_path)


def test_import_is_idempotent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE, f)
        path = f.name
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as dbf:
            db_path = dbf.name
        import_exercises(path, db_path)
        import_exercises(path, db_path)
        conn = get_connection(__import__("pathlib").Path(db_path))
        total = conn.execute("SELECT COUNT(*) FROM exercise_templates WHERE source='free_exercise_db'").fetchone()[0]
        assert total == 2
        conn.close()
    finally:
        os.unlink(path)
        os.unlink(db_path)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/test_import_exercises.py -v
```

- [ ] **Step 3: Write `scripts/import_exercises.py`**

```python
"""
Bulk import free-exercise-db exercises into the workout tracker database.

Usage:
    python -m scripts.import_exercises <path_to_exercises_json> [db_path]

Download from:
    https://github.com/yuhonas/free-exercise-db
    Use: dist/exercises.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.exercises import ExerciseRepository


def _normalize_exercise(raw: dict) -> dict:
    return {
        "source": "free_exercise_db",
        "source_code": raw.get("id", ""),
        "name": raw.get("name", ""),
        "category": raw.get("category") or None,
        "equipment": raw.get("equipment") or None,
        "force": raw.get("force") or None,
        "level": raw.get("level") or None,
        "mechanic": raw.get("mechanic") or None,
        "primary_muscles": json.dumps(raw.get("primaryMuscles", [])),
        "secondary_muscles": json.dumps(raw.get("secondaryMuscles", [])),
        "instructions": json.dumps(raw.get("instructions", [])),
        "image_paths": json.dumps(raw.get("images", [])),
    }


def import_exercises(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = ExerciseRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        exercises = json.load(f)

    count = 0
    for raw in exercises:
        if not raw.get("name"):
            continue
        normalized = _normalize_exercise(raw)
        source_code = normalized.pop("source_code")
        repo.upsert(source="free_exercise_db", source_code=source_code, **normalized)
        count += 1
        if count % 100 == 0:
            print(f"  Imported {count} exercises...")

    print(f"Done. Imported {count} exercises.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_exercises <path> [db_path]")
        sys.exit(1)
    import_exercises(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_import_exercises.py -v
```

- [ ] **Step 5: Create `bin/import-exercises`**

```bash
#!/usr/bin/env bash
# Import free-exercise-db exercises into the production database.
#
# Usage:
#   bin/import-exercises <path-to-exercises.json-on-host>
#
# Download from: https://github.com/yuhonas/free-exercise-db (dist/exercises.json)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bin/import-exercises <path-to-exercises-json-on-host>" >&2
  exit 1
fi

HOST_FILE="$1"
HOST="192.168.1.76"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/stupidclaw_garageband_ed25519}"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no gregmushen@$HOST"

IMAGE=$($SSH "docker inspect \$(docker ps --filter name=workouttracker-web --format '{{.Names}}' | head -1) --format '{{.Config.Image}}'")

echo "Using image: $IMAGE"
echo "Importing: $HOST_FILE"

$SSH "docker run --rm \
  -v \$(dirname '$HOST_FILE'):/exercise-data \
  -v workouttracker_data:/data \
  --entrypoint python \
  '$IMAGE' \
  -m scripts.import_exercises \
  /exercise-data/\$(basename '$HOST_FILE') \
  /data/workout.db"
```

```bash
chmod +x bin/import-exercises
```

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ --tb=short -q
```

- [ ] **Step 7: Commit**

```bash
git add scripts/import_exercises.py bin/import-exercises tests/test_import_exercises.py
git commit -m "feat: exercise import script for free-exercise-db JSON"
```

---

## Task 7: Workout Session Models + Repository + Routes

**Files:**
- Create: `app/models/workout.py` (session portion)
- Create: `app/repositories/workouts.py` (session portion)
- Update: `app/routes/workouts.py` (session endpoints)
- Create: `tests/test_routes_workouts.py` (session tests)

- [ ] **Step 1: Write failing session tests**

```python
# tests/test_routes_workouts.py
import pytest
from app.repositories.exercises import ExerciseRepository


def _exercise(db, name="Bench Press"):
    repo = ExerciseRepository(db)
    repo.ensure_fts()
    return repo.create(source="custom", name=name, equipment="barbell", category="strength")


# --- Sessions ---

def test_create_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"})
    assert r.status_code == 201
    assert r.json()["title"] == "Push"
    assert r.json()["date"] == "2026-05-19"


def test_get_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.get(f"/workouts/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == sid


def test_list_sessions(client, db):
    client.post("/workouts/sessions", json={"date": "2026-05-18", "title": "Pull"})
    client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"})
    r = client.get("/workouts/sessions?start=2026-05-18&end=2026-05-19")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_close_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.post(f"/workouts/sessions/{sid}/close", json={"notes": "great session"})
    assert r2.status_code == 200
    assert r2.json()["ended_at"] is not None
    assert r2.json()["notes"] == "great session"


def test_update_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.patch(f"/workouts/sessions/{sid}", json={"title": "Legs", "energy_score": 8})
    assert r2.status_code == 200
    assert r2.json()["title"] == "Legs"
    assert r2.json()["energy_score"] == 8


def test_delete_session(client, db):
    r = client.post("/workouts/sessions", json={"date": "2026-05-19"})
    sid = r.json()["id"]
    r2 = client.delete(f"/workouts/sessions/{sid}")
    assert r2.status_code == 204
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_routes_workouts.py -v -k "session"
```

- [ ] **Step 3: Write `app/models/workout.py`**

```python
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
```

- [ ] **Step 4: Write `app/repositories/workouts.py` (session methods)**

```python
import sqlite3
from datetime import datetime, date


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
        values = list(kwargs.values()) + [session_id]
        self.conn.execute(
            f"UPDATE workout_sessions SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def close_session(self, session_id: int, **kwargs) -> dict | None:
        updates = {"ended_at": datetime.now().isoformat()}
        updates.update(kwargs)
        self.update_session(session_id, **{k: v for k, v in updates.items() if v is not None})
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
        row = self.conn.execute("SELECT * FROM workout_sets WHERE id = ?", (set_id,)).fetchone()
        return dict(row) if row else None

    def list_sets(self, session_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM workout_sets WHERE session_id = ? ORDER BY set_number, id",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_set(self, set_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [set_id]
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
        """Return last N sessions' sets for an exercise, grouped by session."""
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
        """Best estimated 1RM per exercise (max weight * (1 + reps/30))."""
        rows = self.conn.execute(
            """SELECT ws.exercise_template_id, e.name,
                      MAX(ws.weight * (1.0 + COALESCE(ws.reps, 1) / 30.0)) as estimated_1rm,
                      ws.weight as best_weight, ws.weight_unit, ws.reps as best_reps
               FROM workout_sets ws
               JOIN workout_sessions s ON s.id = ws.session_id
               JOIN exercise_templates e ON e.id = ws.exercise_template_id
               WHERE s.user_id = ? AND ws.weight IS NOT NULL
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

        set_params = [user_id] + q_params[1:]
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
```

- [ ] **Step 5: Write session endpoints in `app/routes/workouts.py`**

```python
from fastapi import APIRouter, HTTPException, Request
from app.models.workout import (
    WorkoutSessionCreate, WorkoutSessionUpdate, WorkoutSessionOut,
    WorkoutSetCreate, WorkoutSetUpdate, WorkoutSetOut,
    BulkSetIn, SessionCloseIn,
)
from app.repositories.workouts import WorkoutRepository
from app.repositories.exercises import ExerciseRepository
from app.services.exercise_search import ExerciseSearchService
from app.services.workout_stats import WorkoutStats

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _repo(request: Request) -> WorkoutRepository:
    return WorkoutRepository(request.app.state.db)


def _ex_svc(request: Request) -> ExerciseSearchService:
    return ExerciseSearchService(ExerciseRepository(request.app.state.db))


# --- Sessions ---

@router.post("/sessions", status_code=201, response_model=WorkoutSessionOut)
def create_session(request: Request, body: WorkoutSessionCreate):
    repo = _repo(request)
    sid = repo.create_session(**body.model_dump(exclude_none=True))
    return repo.get_session(sid)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionOut)
def get_session(request: Request, session_id: int):
    s = _repo(request).get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.get("/sessions", response_model=list[WorkoutSessionOut])
def list_sessions(request: Request, start: str | None = None, end: str | None = None):
    return _repo(request).list_sessions(start=start, end=end)


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionOut)
def update_session(request: Request, session_id: int, body: WorkoutSessionUpdate):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    repo.update_session(session_id, **body.model_dump(exclude_unset=True))
    return repo.get_session(session_id)


@router.post("/sessions/{session_id}/close", response_model=WorkoutSessionOut)
def close_session(request: Request, session_id: int, body: SessionCloseIn):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    return repo.close_session(session_id, **body.model_dump(exclude_none=True))


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(request: Request, session_id: int):
    if not _repo(request).delete_session(session_id):
        raise HTTPException(404, "Session not found")


# --- Sets ---

@router.post("/sessions/{session_id}/sets", status_code=201, response_model=WorkoutSetOut)
def create_set(request: Request, session_id: int, body: WorkoutSetCreate):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    set_id = repo.create_set(session_id=session_id, **body.model_dump(exclude_none=True))
    return repo.get_set(set_id)


@router.post("/sessions/{session_id}/sets/bulk", status_code=201,
             response_model=list[WorkoutSetOut])
def bulk_create_sets(request: Request, session_id: int, body: BulkSetIn):
    repo = _repo(request)
    if not repo.get_session(session_id):
        raise HTTPException(404, "Session not found")
    ex = _ex_svc(request).resolve(body.exercise_query)
    if not ex:
        raise HTTPException(404, f"Exercise not found: '{body.exercise_query}'")
    sets = [s.model_dump(exclude_none=True) for s in body.sets]
    ids = repo.bulk_create_sets(session_id, ex["id"], sets)
    return [repo.get_set(i) for i in ids]


@router.patch("/sets/{set_id}", response_model=WorkoutSetOut)
def update_set(request: Request, set_id: int, body: WorkoutSetUpdate):
    repo = _repo(request)
    if not repo.get_set(set_id):
        raise HTTPException(404, "Set not found")
    repo.update_set(set_id, **body.model_dump(exclude_unset=True))
    return repo.get_set(set_id)


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(request: Request, set_id: int):
    if not _repo(request).delete_set(set_id):
        raise HTTPException(404, "Set not found")


# --- History / Progress ---

@router.get("/recent")
def recent(request: Request, exercise_id: int, limit: int = 5):
    sets = _repo(request).recent_sets_for_exercise(exercise_id, limit=limit)
    return WorkoutStats().format_recent(sets, limit=limit)


@router.get("/progress")
def progress(request: Request, exercise_id: int,
             start: str | None = None, end: str | None = None):
    sets = _repo(request).progress_for_exercise(exercise_id, start=start, end=end)
    return WorkoutStats().format_progress(sets)


@router.get("/personal-records")
def personal_records(request: Request):
    return _repo(request).personal_records()


@router.get("/summary")
def summary(request: Request, start: str | None = None, end: str | None = None):
    return _repo(request).summary(start=start, end=end)
```

- [ ] **Step 6: Run session tests — verify they pass**

```bash
pytest tests/test_routes_workouts.py -v -k "session"
```

- [ ] **Step 7: Commit**

```bash
git add app/ tests/
git commit -m "feat: workout session models, repository, and routes"
```

---

## Task 8: Workout Stats Service + Set/Bulk/History Tests

**Files:**
- Create: `app/services/workout_stats.py`
- Create: `tests/test_workout_stats.py`
- Complete: `tests/test_routes_workouts.py` (set + bulk + history tests)

- [ ] **Step 1: Write failing stats tests**

```python
# tests/test_workout_stats.py
from app.services.workout_stats import WorkoutStats

stats = WorkoutStats()


def test_epley_1rm_single_rep():
    # 225 * (1 + 1/30) = 225 * 1.0333 ≈ 232.5
    result = stats.epley_1rm(225, 1)
    assert abs(result - 232.5) < 1.0


def test_epley_1rm_reps():
    # 225 * (1 + 5/30) = 225 * 1.1667 ≈ 262.5
    result = stats.epley_1rm(225, 5)
    assert abs(result - 262.5) < 1.0


def test_top_set_picks_highest_e1rm():
    sets = [
        {"weight": 225, "reps": 5, "weight_unit": "lb", "set_type": "working"},
        {"weight": 245, "reps": 2, "weight_unit": "lb", "set_type": "working"},
        {"weight": 135, "reps": 10, "weight_unit": "lb", "set_type": "warmup"},
    ]
    top = stats.top_set(sets)
    assert top["weight"] == 225  # higher e1RM: 262.5 vs 261.3


def test_top_set_ignores_warmup():
    sets = [
        {"weight": 300, "reps": 5, "set_type": "warmup"},
        {"weight": 225, "reps": 5, "set_type": "working"},
    ]
    top = stats.top_set(sets)
    assert top["weight"] == 225


def test_total_volume():
    sets = [
        {"weight": 135, "reps": 8},
        {"weight": 155, "reps": 5},
        {"weight": 165, "reps": 3},
    ]
    assert stats.total_volume(sets) == 135*8 + 155*5 + 165*3


def test_format_progress_groups_by_session():
    sets = [
        {"session_id": 1, "date": "2026-05-01", "weight": 135, "reps": 8, "set_type": "working", "weight_unit": "lb"},
        {"session_id": 1, "date": "2026-05-01", "weight": 155, "reps": 5, "set_type": "working", "weight_unit": "lb"},
        {"session_id": 2, "date": "2026-05-08", "weight": 140, "reps": 8, "set_type": "working", "weight_unit": "lb"},
    ]
    result = stats.format_progress(sets)
    assert len(result["sessions"]) == 2
    assert result["sessions"][0]["date"] == "2026-05-01"
    assert result["best_e1rm"] > 0
```

```python
# Add to tests/test_routes_workouts.py

def _session(client):
    return client.post("/workouts/sessions", json={"date": "2026-05-19", "title": "Push"}).json()["id"]


def test_create_set(client, db):
    eid = _exercise(db)
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid,
        "weight": 135,
        "weight_unit": "lb",
        "reps": 8,
        "set_type": "working",
    })
    assert r.status_code == 201
    assert r.json()["weight"] == 135
    assert r.json()["reps"] == 8


def test_bulk_create_sets(client, db):
    eid = _exercise(db, "Barbell Bench Press")
    ExerciseRepository(db).add_alias(eid, "bench")
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets/bulk", json={
        "exercise_query": "bench",
        "sets": [
            {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
            {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
            {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"},
        ],
    })
    assert r.status_code == 201
    assert len(r.json()) == 3
    assert r.json()[0]["weight"] == 135


def test_bulk_sets_unknown_exercise(client, db):
    sid = _session(client)
    r = client.post(f"/workouts/sessions/{sid}/sets/bulk", json={
        "exercise_query": "xyzzy_unknown",
        "sets": [{"weight": 100, "weight_unit": "lb", "reps": 5}],
    })
    assert r.status_code == 404


def test_recent(client, db):
    eid = _exercise(db)
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "weight": 135,
        "weight_unit": "lb", "reps": 8, "set_type": "working",
    })
    r = client.get(f"/workouts/recent?exercise_id={eid}")
    assert r.status_code == 200


def test_personal_records(client, db):
    eid = _exercise(db)
    sid = _session(client)
    client.post(f"/workouts/sessions/{sid}/sets", json={
        "exercise_template_id": eid, "weight": 225,
        "weight_unit": "lb", "reps": 5, "set_type": "working",
    })
    r = client.get("/workouts/personal-records")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_summary(client, db):
    r = client.get("/workouts/summary")
    assert r.status_code == 200
    assert "sessions" in r.json()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_workout_stats.py tests/test_routes_workouts.py -v
```

- [ ] **Step 3: Write `app/services/workout_stats.py`**

```python
from itertools import groupby


class WorkoutStats:
    def epley_1rm(self, weight: float, reps: float) -> float:
        return round(weight * (1 + reps / 30), 1)

    def top_set(self, sets: list[dict]) -> dict | None:
        working = [
            s for s in sets
            if s.get("set_type") in ("working", "amrap", "failure")
            and s.get("weight") is not None
        ]
        if not working:
            return None
        return max(
            working,
            key=lambda s: self.epley_1rm(s["weight"], s.get("reps") or 1),
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
            e1rm = self.epley_1rm(top["weight"], top.get("reps") or 1) if top else 0
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
```

- [ ] **Step 4: Run all tests — verify they pass**

```bash
pytest tests/ --tb=short -q
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/ tests/
git commit -m "feat: workout sets, bulk logging, history, progress, e1RM stats"
```

---

## Task 9: README, Push, CI Verification, Exercise Data Import

**Files:**
- Update: `README.md`

- [ ] **Step 1: Update `README.md`**

```markdown
# Workout Tracker

A personal lifting and workout tracking API built with FastAPI and SQLite.

**Live:** https://wt.paracosmlab.com — OpenAPI schema at `/openapi.json`

## What it does

REST API for logging strength training sessions, sets, and tracking progress.

Key endpoints:
- `GET /exercises/search?q=` — full-text search with alias support (e.g. "bench" → Barbell Bench Press)
- `POST /workouts/sessions` — start a workout session
- `POST /workouts/sessions/{id}/sets/bulk` — log multiple sets in one call
- `GET /workouts/recent?exercise_id=` — last N sessions for an exercise
- `GET /workouts/progress?exercise_id=` — e1RM trend and volume over time
- `GET /workouts/personal-records` — best estimated 1RM per exercise
- `POST /workouts/sessions/{id}/close` — close out a session

All endpoints require `Authorization: Bearer <token>`.

## Stack

Python 3.12, FastAPI, SQLite (WAL + FTS5), Kamal 2, Woodpecker CI, Cloudflare tunnel.

## Local development

```bash
pip install -e ".[dev]"
pytest tests/
```

## Exercise data import

Download [free-exercise-db](https://github.com/yuhonas/free-exercise-db):

```bash
# On garageband:
wget -O /home/gregmushen/workout-data/exercises.json \
  "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"

bin/import-exercises /home/gregmushen/workout-data/exercises.json
```

Re-running is safe — exercises are upserted by `(source, source_code)`.

## Bulk set logging

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_query": "bench",
    "sets": [
      {"weight": 135, "weight_unit": "lb", "reps": 8, "set_type": "working"},
      {"weight": 155, "weight_unit": "lb", "reps": 5, "set_type": "working"},
      {"weight": 165, "weight_unit": "lb", "reps": 3, "set_type": "working"}
    ]
  }' \
  "https://wt.paracosmlab.com/workouts/sessions/1/sets/bulk"
```
```

- [ ] **Step 2: Run full test suite one final time**

```bash
pytest tests/ --tb=short -q
```

Expected: all PASS

- [ ] **Step 3: Push to GitHub — CI runs**

```bash
git add README.md
git commit -m "docs: README with import instructions and bulk set example"
git push origin master
```

- [ ] **Step 4: Before first deploy — set up Cloudflare + Woodpecker secrets**

Do these manually on the Cloudflare dashboard and in Woodpecker UI:

1. Create a new Cloudflare tunnel named `workouttracker`
2. Add ingress: `wt.paracosmlab.com` → `http://kamal-proxy:80`
3. Add CNAME DNS record: `wt` → `<tunnel-id>.cfargotunnel.com`
4. Copy the tunnel token
5. In Woodpecker UI → repo settings → secrets, add:
   - `deploy_ssh_key` (same key as nutrition tracker)
   - `WT_BEARER_TOKEN` (choose a bearer token)
   - `CLOUDFLARE_TUNNEL_TOKEN` (the tunnel token from step 4)
   - `KAMAL_REGISTRY_PASSWORD` (same as nutrition tracker)

- [ ] **Step 5: Verify CI passes and app is live**

```bash
curl -s https://wt.paracosmlab.com/health
# Expected: {"status":"ok","version":"0.1.0"}

curl -s -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  "https://wt.paracosmlab.com/exercises/search?q=squat"
# Expected: [] (empty until exercise data imported)
```

- [ ] **Step 6: Download and import exercise data**

```bash
# On garageband:
ssh gregmushen@192.168.1.76 \
  "mkdir -p /home/gregmushen/workout-data && \
   wget -q -O /home/gregmushen/workout-data/exercises.json \
   'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json'"

# Run import (from local machine):
bin/import-exercises /home/gregmushen/workout-data/exercises.json
```

Expected: `Done. Imported 873 exercises.`

- [ ] **Step 7: Verify exercise search works**

```bash
curl -s -H "Authorization: Bearer $WT_BEARER_TOKEN" \
  "https://wt.paracosmlab.com/exercises/search?q=squat&limit=3" | python3 -m json.tool
```

Expected: array with squat variations, each with `equipment`, `primary_muscles`, etc.

---

## Task 10: CLI Commands (nutrition-pp-cli workout extension)

**Files:**
- Modify: `nutritiontracker/app/cli/workout.py` (new file in nutrition tracker repo)
- Modify: `nutritiontracker/pyproject.toml` (add `workout` CLI entry point or extend existing)

> **Note:** CLI commands live in the `nutritiontracker` repo because the spec uses `nutrition-pp-cli workout ...` naming. This task extends the existing nutrition tracker CLI with a `workout` subcommand group.

**Shorthand parsing:** `135x8` → weight=135, unit=lb, reps=8. `60kgx5` → weight=60, unit=kg, reps=5. `plank 60s` → duration_seconds=60.

- [ ] **Step 1: Write failing CLI tests in nutritiontracker**

```python
# nutritiontracker/tests/test_cli_workout.py
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from app.cli.workout import workout


runner = CliRunner()


def test_parse_shorthand_lb():
    from app.cli.workout import _parse_set
    result = _parse_set("135x8")
    assert result == {"weight": 135.0, "weight_unit": "lb", "reps": 8.0}


def test_parse_shorthand_kg():
    from app.cli.workout import _parse_set
    result = _parse_set("60kgx5")
    assert result == {"weight": 60.0, "weight_unit": "kg", "reps": 5.0}


def test_parse_timed():
    from app.cli.workout import _parse_set
    result = _parse_set("60s")
    assert result == {"duration_seconds": 60}


def test_workout_today_invokes_api(monkeypatch):
    with patch("app.cli.workout._get") as mock_get:
        mock_get.return_value = {"sessions": []}
        result = runner.invoke(workout, ["today"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd ../nutritiontracker
pytest tests/test_cli_workout.py -v
```

- [ ] **Step 3: Write `app/cli/workout.py` in nutritiontracker**

```python
"""workout CLI subcommands — talk to the workout tracker API."""
import json
import re
import os
import httpx
import click

WT_BASE = os.environ.get("WT_BASE_URL", "https://wt.paracosmlab.com")
WT_TOKEN = os.environ.get("WT_BEARER_TOKEN", "")


def _headers():
    return {"Authorization": f"Bearer {WT_TOKEN}"}


def _get(path: str, **params) -> dict | list:
    r = httpx.get(f"{WT_BASE}{path}", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict | list:
    r = httpx.post(f"{WT_BASE}{path}", headers=_headers(), json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def _patch(path: str, body: dict) -> dict:
    r = httpx.patch(f"{WT_BASE}{path}", headers=_headers(), json=body, timeout=10)
    r.raise_for_status()
    return r.json()


def _parse_set(s: str) -> dict:
    """Parse shorthand like '135x8', '60kgx5', 'bwx12', 'plank 60s'."""
    s = s.strip()
    # timed: '60s' or 'plank 60s'
    timed = re.search(r"(\d+)s$", s)
    if timed and not re.search(r"x", s):
        return {"duration_seconds": int(timed.group(1)), "reps": None}
    # weight x reps
    m = re.match(r"^(bw|(\d+(?:\.\d+)?)(kg|lb)?)x(\d+(?:\.\d+)?)$", s, re.IGNORECASE)
    if m:
        if m.group(1).lower() == "bw":
            return {"reps": float(m.group(4)), "set_type": "bodyweight"}
        weight = float(m.group(2))
        unit = (m.group(3) or "lb").lower()
        reps = float(m.group(4))
        return {"weight": weight, "weight_unit": unit, "reps": reps}
    raise click.BadParameter(f"Cannot parse set: '{s}'. Use format like '135x8', '60kgx5', 'bwx12', '60s'")


@click.group()
def workout():
    """Workout tracking commands."""
    pass


@workout.command("start")
@click.option("--title", default=None)
@click.option("--date", default=None, help="Date (YYYY-MM-DD). Defaults to today.")
def start(title, date):
    """Start a new workout session."""
    import datetime
    body = {"date": date or datetime.date.today().isoformat()}
    if title:
        body["title"] = title
    session = _post("/workouts/sessions", body)
    click.echo(f"Session {session['id']} started — {session.get('title', session['date'])}")


@workout.command("today")
@click.option("--agent", is_flag=True, help="Output raw JSON")
def today(agent):
    """Show today's open workout session."""
    import datetime
    today_str = datetime.date.today().isoformat()
    data = _get("/workouts/sessions", start=today_str, end=today_str)
    if agent:
        click.echo(json.dumps(data))
    else:
        if not data:
            click.echo("No workout today yet. Use: workout start")
        else:
            for s in data:
                status = "open" if not s.get("ended_at") else "closed"
                click.echo(f"[{s['id']}] {s.get('title', s['date'])} ({status})")


@workout.command("add-set")
@click.option("--exercise", required=True)
@click.option("--session", "session_id", default=None, type=int, help="Session ID. Defaults to latest open.")
@click.option("--weight", type=float, default=None)
@click.option("--lb", "unit", flag_value="lb", default=True)
@click.option("--kg", "unit", flag_value="kg")
@click.option("--reps", type=float, default=None)
@click.option("--type", "set_type", default="working")
def add_set(exercise, session_id, weight, unit, reps, set_type):
    """Log a single set."""
    ex_results = _get("/exercises/search", q=exercise, limit=1)
    if not ex_results:
        raise click.ClickException(f"Exercise not found: '{exercise}'")
    ex = ex_results[0]
    if session_id is None:
        import datetime
        today_str = datetime.date.today().isoformat()
        sessions = _get("/workouts/sessions", start=today_str, end=today_str)
        open_sessions = [s for s in sessions if not s.get("ended_at")]
        if not open_sessions:
            raise click.ClickException("No open session today. Use: workout start")
        session_id = open_sessions[0]["id"]
    body = {"exercise_template_id": ex["id"], "set_type": set_type}
    if weight is not None:
        body["weight"] = weight
        body["weight_unit"] = unit
    if reps is not None:
        body["reps"] = reps
    result = _post(f"/workouts/sessions/{session_id}/sets", body)
    click.echo(f"Set logged: {ex['name']} {result.get('weight', '')} {result.get('weight_unit', '')} x {result.get('reps', '')}")


@workout.command("add-bulk")
@click.option("--exercise", required=True)
@click.argument("sets_str")
@click.option("--session", "session_id", default=None, type=int)
def add_bulk(exercise, sets_str, session_id):
    """Log multiple sets. E.g.: workout add-bulk --exercise bench '135x8,155x5,165x3'"""
    if session_id is None:
        import datetime
        today_str = datetime.date.today().isoformat()
        sessions = _get("/workouts/sessions", start=today_str, end=today_str)
        open_sessions = [s for s in sessions if not s.get("ended_at")]
        if not open_sessions:
            raise click.ClickException("No open session today. Use: workout start")
        session_id = open_sessions[0]["id"]
    sets = [_parse_set(s.strip()) for s in sets_str.split(",")]
    body = {"exercise_query": exercise, "sets": sets}
    results = _post(f"/workouts/sessions/{session_id}/sets/bulk", body)
    click.echo(f"Logged {len(results)} sets for {exercise}")


@workout.command("recent")
@click.option("--exercise", required=True)
@click.option("--limit", default=5)
@click.option("--agent", is_flag=True)
def recent(exercise, limit, agent):
    """Show recent sets for an exercise."""
    ex_results = _get("/exercises/search", q=exercise, limit=1)
    if not ex_results:
        raise click.ClickException(f"Exercise not found: '{exercise}'")
    data = _get("/workouts/recent", exercise_id=ex_results[0]["id"], limit=limit)
    if agent:
        click.echo(json.dumps(data))
    else:
        for s in data.get("sessions", []):
            top = s.get("top_set")
            top_str = f"{top['weight']}{top.get('weight_unit','lb')} x {top['reps']}" if top else "—"
            click.echo(f"  {s['date']} — top: {top_str} — vol: {s.get('volume', 0):.0f}")


@workout.command("progress")
@click.option("--exercise", required=True)
@click.option("--agent", is_flag=True)
def progress(exercise, agent):
    """Show e1RM progress for an exercise."""
    ex_results = _get("/exercises/search", q=exercise, limit=1)
    if not ex_results:
        raise click.ClickException(f"Exercise not found: '{exercise}'")
    data = _get("/workouts/progress", exercise_id=ex_results[0]["id"])
    if agent:
        click.echo(json.dumps(data))
    else:
        click.echo(f"Best e1RM: {data.get('best_e1rm', 0):.1f} lb  Sessions: {data.get('session_count', 0)}")
        for s in data.get("sessions", []):
            click.echo(f"  {s['date']} — e1RM: {s['estimated_1rm']:.1f}  vol: {s['volume']:.0f}")


@workout.command("close")
@click.option("--session", "session_id", default=None, type=int)
@click.option("--notes", default=None)
@click.option("--energy", default=None, type=int)
@click.option("--soreness", default=None, type=int)
def close(session_id, notes, energy, soreness):
    """Close out the current workout session."""
    if session_id is None:
        import datetime
        today_str = datetime.date.today().isoformat()
        sessions = _get("/workouts/sessions", start=today_str, end=today_str)
        open_sessions = [s for s in sessions if not s.get("ended_at")]
        if not open_sessions:
            raise click.ClickException("No open session to close.")
        session_id = open_sessions[0]["id"]
    body = {}
    if notes:
        body["notes"] = notes
    if energy:
        body["energy_score"] = energy
    if soreness:
        body["soreness_score"] = soreness
    result = _post(f"/workouts/sessions/{session_id}/close", body)
    click.echo(f"Session {result['id']} closed at {result['ended_at']}")
    if notes:
        click.echo(f"Notes: {notes}")
```

- [ ] **Step 4: Register `workout` subcommand in nutritiontracker CLI entry point**

Find the existing CLI entry point in `nutritiontracker/` and add:
```python
from app.cli.workout import workout
cli.add_command(workout)
```

(Exact location depends on how `nutrition-pp-cli` is wired up in that repo — check `pyproject.toml` `[project.scripts]` and follow the pattern.)

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd ../nutritiontracker
pytest tests/test_cli_workout.py -v
```

- [ ] **Step 6: Run full nutrition tracker test suite**

```bash
pytest tests/ --tb=short -q
```

- [ ] **Step 7: Commit to nutritiontracker**

```bash
git add app/cli/workout.py tests/test_cli_workout.py
git commit -m "feat: workout CLI subcommands (start, today, add-set, add-bulk, recent, progress, close)"
```

---

## Explicitly Deferred

The following spec items are explicitly deferred to separate implementation efforts:

**Hermes `pp-lifting` skill** (spec MVP Build Order item 9): Hermes lives in a separate repo/skill system. It will call the workout tracker API endpoints built here. Defer to a dedicated Hermes skill implementation once the API is live and validated.

**`POST /imports/exercises/free-exercise-db` HTTP endpoint** (spec Exercise Import section): The spec itself says "For production, prefer a CLI/script import rather than uploading a large JSON file through HTTP." The CLI import (`bin/import-exercises`) satisfies the spec's own recommendation. The HTTP endpoint is deferred.
