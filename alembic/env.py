from logging.config import fileConfig
import os
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
    from sqlalchemy import create_engine

    db_path = Path(os.environ.get("WT_DB_PATH", "data/workout.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    connectable = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
