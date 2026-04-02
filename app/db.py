import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def init_db() -> None:
    if not engine:
        return
    # Imported here to avoid circular imports
    from app import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Database unavailable; tables not created (%s)", exc)
