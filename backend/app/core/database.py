"""SQLAlchemy 2.0 engine, session factory, and declarative base."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Serverless-friendly engine. NullPool keeps no long-lived process pool — on
# Vercel each invocation is ephemeral, and connection pooling is delegated to
# Neon's PgBouncer pooler (the `-pooler` host). This avoids stale sockets that
# a process-level pool would carry across frozen/thawed function instances.
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    future=True,
)


@event.listens_for(engine, "connect")
def _disable_prepared_statements(dbapi_connection, _record) -> None:
    """psycopg3 caches server-side prepared statements per connection, which
    breaks under PgBouncer *transaction* pooling (the next statement may land
    on a different backend). Disabling them keeps the pooled endpoint safe."""
    try:
        dbapi_connection.prepare_threshold = None
    except AttributeError:
        pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
