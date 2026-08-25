"""store ingest 검증 — 업서트(신규 삽입 + 상태 변경 갱신) 시맨틱."""

from collections.abc import Iterator
from datetime import date, datetime

from sqlalchemy import delete, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.app.ports.output.store_port import StorePermitGatewayPort
from apps.store.app.use_cases.store_interactor import StoreInteractor
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-store-"
_TARGET = IngestTarget(
    industry_id="karaoke", slug="karaoke_rooms", district_code="11110", authority_code="3000000"
)


def _store(n: int, status_code: str = "01", updated: int = 1) -> Store:
    return Store(
        store_id=f"{_TEST_PREFIX}{n}",
        name=f"업소 {n}",
        industry_id=_TARGET.industry_id,
        district_code=_TARGET.district_code,
        open_date=date(2020, 1, n),
        close_date=None,
        status_code=status_code,
        status_name="영업" if status_code == "01" else "폐업",
        lat=37.5,
        lng=127.0,
        source_updated_at=datetime(2026, 8, updated, 12, 0),
    )


class FakeGateway(StorePermitGatewayPort):
    def __init__(self, stores: list[Store]) -> None:
        self._stores = stores

    def iter_stores(self, target: IngestTarget, updated_since: datetime | None) -> Iterator[Store]:
        yield from self._stores


def _cleanup():
    with session_scope() as session:
        session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_TEST_PREFIX}%")))


def test_ingest_upserts_new_and_changed_rows():
    _cleanup()
    repository = SqlAlchemyStoreRepository()

    first = StoreInteractor(repository, FakeGateway([_store(1), _store(2)])).ingest([_TARGET])
    assert first == 2

    # 2번 업소가 폐업으로 갱신된 상황
    changed = StoreInteractor(
        repository, FakeGateway([_store(2, status_code="03", updated=2)])
    ).ingest([_TARGET])
    assert changed == 1

    with session_scope() as session:
        rows = {
            r.store_id: r.status_code
            for r in session.execute(
                select(StoreOrm).where(StoreOrm.store_id.like(f"{_TEST_PREFIX}%"))
            ).scalars()
        }
    assert rows == {f"{_TEST_PREFIX}1": "01", f"{_TEST_PREFIX}2": "03"}
    _cleanup()


def test_latest_source_updated_at_returns_cursor():
    _cleanup()
    repository = SqlAlchemyStoreRepository()
    StoreInteractor(repository, FakeGateway([_store(1, updated=3)])).ingest([_TARGET])

    cursor = repository.latest_source_updated_at(_TARGET.industry_id, _TARGET.district_code)
    assert cursor == datetime(2026, 8, 3, 12, 0)
    _cleanup()
