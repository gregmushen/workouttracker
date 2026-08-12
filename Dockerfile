FROM python:3.12-slim

WORKDIR /app

# Everything the hatchling build reads must exist before pip runs. pyproject
# declares packages = ["workouttracker", "scripts"] and force-includes alembic
# and alembic.ini, so installing before copying them fails with
# "Forced include not found: /app/alembic".
COPY pyproject.toml README.md alembic.ini ./
COPY alembic/ ./alembic/
COPY workouttracker/ ./workouttracker/
COPY scripts/ ./scripts/

RUN pip install --no-cache-dir -e .

COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
