# Deployment

Workout Tracker includes a Kamal 2 deployment configuration and a Woodpecker CI pipeline. The configuration is intentionally generic so the same repository can deploy to any Docker-capable host.

## Required Secrets

Set these in your CI/deploy environment:

```text
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
REGISTRY_SERVER
REGISTRY_USERNAME
KAMAL_REGISTRY_PASSWORD
APP_HOST
WT_BEARER_TOKEN
CLOUDFLARE_TUNNEL_TOKEN
```

## Runtime Shape

- The application container runs the FastAPI app.
- SQLite is stored in the `workouttracker_data` Docker volume at `/data/workout.db`.
- Exercise images are served from `/exercise-images/...`.
- Cloudflared is configured as a Kamal accessory.

## CI Pipeline

Woodpecker runs:

1. `ruff check workouttracker/ tests/ scripts/`
2. `gitleaks detect`
3. `pytest tests/ --tb=short -q`
4. `kamal deploy`
5. `kamal accessory boot cloudflared` or accessory reboot

The deploy step uses a Ruby image because Kamal is distributed as a Ruby gem. That image is deployment tooling only; the application runtime is Python.

## Manual Deploy

Install Kamal, configure the same environment variables, then run:

```bash
kamal deploy
```

To open a shell in the running app:

```bash
kamal app exec --interactive --reuse "sh"
```

## Exercise Import

After deploying, import the exercise database into the production SQLite volume:

```bash
bin/import-exercises /path/to/free-exercise-db/dist/exercises.json
```

The import helper detects the currently running container image, mounts the exercise data file into a throwaway container, and writes into the production database volume.
