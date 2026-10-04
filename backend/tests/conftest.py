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
_dev_url = None
_test_url = None


def pytest_configure(config: pytest.Config) -> None:
    """순수 로직 테스트를 위한 marker 등록 및 환경변수 초기화."""
    global _dev_url, _test_url
    config.addinivalue_line("markers", "no_db: 데이터베이스 없이 실행 가능한 순수 로직 테스트")
    # get_settings()·get_engine() 은 lru_cache — 어떤 테스트도 DB 에 붙기 전에 환경변수를 바꾼다 (환경변수 > .env)
    try:
        _dev_url = make_url(get_settings().database_url)
        _test_url = _dev_url.set(database=f"{_dev_url.database}{_TEST_DB_SUFFIX}")
        os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)
    except Exception:
        # DB 설정이 없어도 no_db 테스트는 통과할 수 있도록
        pass
    # TestClient는 http라 Secure 쿠키를 돌려보내지 않고, 구글은 테스트마다 가짜로 주입한다 — 개발 .env 값에 흔들리지 않게 고정
    os.environ["ADMIN_COOKIE_SECURE"] = "false"
    for _key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
        os.environ[_key] = ""
    get_settings.cache_clear()


def _create_database_if_missing() -> None:
    if _dev_url is None or _test_url is None:
        return
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
def test_database(request) -> None:
    """DB 초기화 — no_db 마크가 있는 테스트만 있으면 스킵."""
    # 세션에 no_db 마크가 없는 테스트가 있으면 DB 초기화 필요
    has_non_no_db_tests = any("no_db" not in item.keywords for item in request.session.items)
    if not has_non_no_db_tests:
        return

    database = make_url(get_settings().database_url).database
    assert database.endswith(_TEST_DB_SUFFIX), f"테스트가 개발 DB({database})를 가리킨다 — 중단"

    from apps.master.adapter.inbound.cli.seed_master import seed_all

    _create_database_if_missing()
    command.upgrade(Config(str(_BACKEND_DIR / "alembic.ini")), "head")
    seed_all()
