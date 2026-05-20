FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY workouttracker/ ./workouttracker/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
