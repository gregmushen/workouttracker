# Exercise Data Import

Workout Tracker can seed its exercise library from `free-exercise-db`.

## Source

- Project: `free-exercise-db`
- Repository: https://github.com/yuhonas/free-exercise-db
- License: Unlicense / public domain

Data used:

- exercise names
- categories
- equipment
- force
- level
- mechanic
- primary muscles
- secondary muscles
- instructions
- image paths

## Download JSON

```bash
mkdir -p data
curl -L \
  -o data/exercises.json \
  "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
```

## Import JSON

```bash
python -m scripts.import_exercises data/exercises.json ./data/workout.db
```

The import is idempotent. Exercises are upserted by `(source, source_code)`.

## Import With Images

Clone `free-exercise-db` locally so the image files are available:

```bash
git clone https://github.com/yuhonas/free-exercise-db /tmp/free-exercise-db
```

Import JSON and copy images:

```bash
python -m scripts.import_exercises \
  /tmp/free-exercise-db/dist/exercises.json \
  ./data/workout.db \
  --images-root /tmp/free-exercise-db/exercises \
  --public-images-root public/exercise-images
```

The importer copies referenced image files to:

```text
public/exercise-images/
```

The database stores relative paths, not image binaries.

## Flags

Dry run:

```bash
python -m scripts.import_exercises data/exercises.json ./data/workout.db --dry-run
```

Deactivate missing imported records:

```bash
python -m scripts.import_exercises data/exercises.json ./data/workout.db --deactivate-missing
```

`--deactivate-missing` only applies to imported `free_exercise_db` records. It does not delete custom exercises.

## Production Import Helper

The `bin/import-exercises` helper can run the importer inside the currently deployed Docker image.

Required environment:

```bash
export DEPLOY_HOST="your-docker-host"
export DEPLOY_USER="deploy"
export SSH_KEY="$HOME/.ssh/deploy_key"
```

Run:

```bash
bin/import-exercises /path/on/host/exercises.json
```

Optional environment:

```bash
export KAMAL_SERVICE="workouttracker"
export WORKOUTTRACKER_DATA_VOLUME="workouttracker_data"
export WT_DB_PATH="/data/workout.db"
```

