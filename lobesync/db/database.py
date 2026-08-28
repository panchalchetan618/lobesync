import logging
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlmodel import Session

from lobesync.config import config

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_engine_url: str | None = None


def get_engine() -> Engine:
    """Return the engine for the current configuration.

    Delaying creation avoids binding to a missing or stale configuration during
    module import, which is important for first-run setup and tests.
    """
    global _engine, _engine_url
    database_url = config.DATABASE_URL
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    if _engine is None or _engine_url != database_url:
        _engine = create_engine(database_url)
        _engine_url = database_url
        if database_url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def init_db() -> None:
    """Bring the configured database to the current Alembic revision."""
    database_url = config.DATABASE_URL
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    logger.info("Applying database migrations")
    alembic_config = AlembicConfig()
    alembic_config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    logger.info("Database migrations complete")


def get_db() -> Generator[Session, None, None]:
    db: Session = Session(get_engine())
    try:
        yield db
    finally:
        db.close()
