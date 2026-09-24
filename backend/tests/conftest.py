"""테스트 DB 분리 — 개발 DB(크론 실적재 대상) 대신 `<db>_test` 를 쓴다.

2026-09-24: test_funding_expiry 의 refresh_expirations(고정 날짜)가 개발 DB funding_program 의
만료 플래그 510건을 전부 되돌림(STATUS §4-1). 세션 시작 시 테스트 DB 생성(없으면) → alembic head →
마스터 시드(멱등, 파일 기반)까지 준비한다.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from core.matrix.grid_keymaker_secret_manager import get_settings

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_TEST_DB_SUFFIX = "_test"

# get_settings()·get_engine() 은 lru_cache — 어떤 테스트도 DB 에 붙기 전에 환경변수를 바꾼다 (환경변수 > .env)
_dev_url = make_url(get_settings().database_url)
_test_url = _dev_url.set(database=f"{_dev_url.database}{_TEST_DB_SUFFIX}")
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)
get_settings.cache_clear()


def _create_database_if_missing() -> None:
    engine = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("select 1 from pg_database where datname = :name"), {"name": _test_url.database}
            ).scalar()
            if not exists:
                connection.execute(text(f'create database "{_test_url.database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    database = make_url(get_settings().database_url).database
    assert database.endswith(_TEST_DB_SUFFIX), f"테스트가 개발 DB({database})를 가리킨다 — 중단"

    from apps.master.adapter.inbound.cli.seed_master import seed_all

    _create_database_if_missing()
    command.upgrade(Config(str(_BACKEND_DIR / "alembic.ini")), "head")
    seed_all()
