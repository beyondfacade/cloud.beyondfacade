"""전역 DB 매니저 — SQLAlchemy engine/session 단일 창구 (pgvector PostgreSQL)."""

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.matrix.grid_keymaker_secret_manager import get_settings


class OrmBase(DeclarativeBase):
    """모든 BC의 ORM 모델이 상속하는 공용 Declarative Base (Alembic 대상)."""


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI Depends용 — 요청 단위 세션. 성공 시 commit, 예외 시 rollback."""
    with session_scope() as session:
        yield session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """배치·스크립트용 — with 블록 단위 세션. 성공 시 commit, 예외 시 rollback."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
