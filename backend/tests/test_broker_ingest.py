"""broker snapshot ingest 검증 — 스냅샷 업서트 + 소실 폐업 추정 + 위치 이월 (실 DB)."""

from collections.abc import Iterator
from datetime import date, datetime

from sqlalchemy import delete, select

from apps.store.adapter.inbound.cli.broker_collector import _GATEWAY_FACTORIES
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.ports.output.broker_snapshot_port import BrokerGatewayPort
from apps.store.app.use_cases.broker_snapshot_interactor import BrokerSnapshotInteractor
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-broker-"
_INDUSTRY = "real_estate"
_DISTRICT = "11110"


def _store(n: int) -> Store:
    return Store(
        store_id=f"{_TEST_PREFIX}{n}",
        name=f"중개사무소 {n}",
        industry_id=_INDUSTRY,
        district_code=_DISTRICT,
        open_date=date(2020, 1, n),
        close_date=None,
        status_code="open",
        status_name="영업중",
        lat=None,
        lng=None,
        source_updated_at=datetime(2026, 9, 7),
    )


class FakeGateway(BrokerGatewayPort):
    def __init__(self, stores: list[Store]) -> None:
        self._stores = stores

    def iter_offices(self, industry_id: str, district_code: str) -> Iterator[Store]:
        yield from self._stores


def _cleanup():
    with session_scope() as session:
        session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_TEST_PREFIX}%")))


def _rows() -> dict[str, StoreOrm]:
    with session_scope() as session:
        rows = session.execute(
            select(StoreOrm).where(StoreOrm.store_id.like(f"{_TEST_PREFIX}%"))
        ).scalars()
        return {
            r.store_id: (r.close_date, r.status_code, r.status_name, r.lat, r.lng, r.region_code)
            for r in rows
        }


def _ingest(stores: list[Store], observed_on: date) -> tuple[int, int]:
    interactor = BrokerSnapshotInteractor(
        repository=SqlAlchemyStoreRepository(), gateway=FakeGateway(stores)
    )
    return interactor.ingest(_INDUSTRY, _DISTRICT, observed_on=observed_on)


def test_first_load_never_estimates_closure():
    _cleanup()
    processed, closed = _ingest([_store(1), _store(2)], observed_on=date(2026, 9, 7))
    assert (processed, closed) == (2, 0)  # 최초 적재일 — 비교 기준 없음, 폐업 추정 발동 금지
    assert all(row[0] is None for row in _rows().values())
    _cleanup()


def test_missing_store_marked_closed_estimated():
    _cleanup()
    _ingest([_store(1), _store(2)], observed_on=date(2026, 9, 7))

    # 다음날 스냅샷에서 2번 소실 → 폐업(추정), 1번은 유지
    processed, closed = _ingest([_store(1)], observed_on=date(2026, 9, 8))
    assert (processed, closed) == (1, 1)

    rows = _rows()
    assert rows[f"{_TEST_PREFIX}1"][0] is None
    assert rows[f"{_TEST_PREFIX}2"][:3] == (date(2026, 9, 8), "closed_estimated", "폐업(추정)")
    _cleanup()


def test_reappearing_store_reopens_and_stays_closed_otherwise():
    _cleanup()
    _ingest([_store(1), _store(2)], observed_on=date(2026, 9, 7))
    _ingest([_store(1)], observed_on=date(2026, 9, 8))  # 2번 폐업(추정)

    # 셋째 날에도 2번 부재 — 이미 폐업 처리된 건은 재추정 대상 아님 (관측일 유지)
    _, closed = _ingest([_store(1)], observed_on=date(2026, 9, 9))
    assert closed == 0
    assert _rows()[f"{_TEST_PREFIX}2"][0] == date(2026, 9, 8)

    # 넷째 날 2번 재등장 — 스냅샷이 진실: 폐업 해제(업서트로 close_date 초기화)
    _, closed = _ingest([_store(1), _store(2)], observed_on=date(2026, 9, 10))
    assert closed == 0
    assert _rows()[f"{_TEST_PREFIX}2"][0] is None
    _cleanup()


def test_upsert_preserves_geocoded_location():
    """원천에 좌표가 없으므로 재수집 업서트가 후속 지오코딩·공간조인 결과를 지우면 안 된다."""
    _cleanup()
    _ingest([_store(1)], observed_on=date(2026, 9, 7))
    with session_scope() as session:  # SGIS 지오코딩 후속이 채웠다고 가정
        row = session.get(StoreOrm, f"{_TEST_PREFIX}1")
        row.lat, row.lng = 37.57, 126.98

    _ingest([_store(1)], observed_on=date(2026, 9, 8))
    assert _rows()[f"{_TEST_PREFIX}1"][3:5] == (37.57, 126.98)
    _cleanup()


def test_gateway_factory_registry_covers_molit_broker():
    gateway = _GATEWAY_FACTORIES["molit_broker"]()
    assert isinstance(gateway, BrokerGatewayPort)
