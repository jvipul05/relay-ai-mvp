"""SQLAlchemy engine, session dependency and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import database_url

_db_url = database_url()
_engine_options = {"pool_pre_ping": True}
if not _db_url.startswith("sqlite"):
    _engine_options["pool_recycle"] = 1800
    _engine_options["pool_size"] = 5
    _engine_options["max_overflow"] = 10
elif _db_url in {"sqlite://", "sqlite:///:memory:"}:
    _engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(_db_url, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
