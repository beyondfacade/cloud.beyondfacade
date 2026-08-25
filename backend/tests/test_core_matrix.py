"""core/matrix 전역 인프라 매니저 검증 — Secret(.env)과 DB 연결."""

from sqlalchemy import text

from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_oracle_database_manager import session_scope


def test_settings_loads_database_url():
    settings = get_settings()
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_is_cached_singleton():
    assert get_settings() is get_settings()


def test_database_connection_select_one():
    with session_scope() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1


def test_pgvector_extension_available():
    with session_scope() as session:
        installed = session.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
    assert installed == 1
