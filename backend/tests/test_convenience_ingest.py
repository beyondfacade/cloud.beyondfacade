"""convenience snapshot ingest 검증 — 멱등 업서트 + first/last_seen 관측 필드 (실 DB).

broker 전례와 달리 close_date 추정을 하지 않는다: 원천(소진공 상가정보)은 개폐업
분석 불가(api.md §2-3)이므로 소실은 last_seen_on 정지로만 남기고 판정은 후속 분석 몫.
"""

from collections.abc import Iterator
from datetime import date

from sqlalchemy import delete, select

from apps.convenience.adapter.outbound.orms.convenience_store_orm import (
    ConvenienceStoreOrm,
)
from apps.convenience.adapter.outbound.repositories.convenience_store_repository import (
    SqlAlchemyConvenienceStoreRepository,
)
from apps.convenience.app.ports.output.convenience_store_port import (
    ConvenienceGatewayPort,
)
from apps.convenience.app.use_cases.convenience_store_interactor import (
    ConvenienceSnapshotInteractor,
)
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-conveni-"


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()


def _store(n: int, region_code: str, name: str | None = None) -> ConvenienceStore:
    return ConvenienceStore(
        store_id=f"{_TEST_PREFIX}{n}",
        name=name or f"씨유시험{n}점",
        branch_name=None,
        brand="CU",
        region_code=region_code,
        lat=37.5,
        lng=127.0,
        road_address=None,
        jibun_address=None,
        source_stdr_ym="202606",
    )


class FakeGateway(ConvenienceGatewayPort):
    def __init__(self, stores: list[ConvenienceStore]) -> None:
        self._stores = stores

    def iter_stores(self, region_code: str) -> Iterator[ConvenienceStore]:
        yield from self._stores


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(ConvenienceStoreOrm).where(
                ConvenienceStoreOrm.store_id.like(f"{_TEST_PREFIX}%")
            )
        )


def _rows() -> dict[str, tuple]:
    with session_scope() as session:
        rows = session.execute(
            select(ConvenienceStoreOrm).where(
                ConvenienceStoreOrm.store_id.like(f"{_TEST_PREFIX}%")
            )
        ).scalars()
        return {r.store_id: (r.first_seen_on, r.last_seen_on, r.name, r.brand) for r in rows}


def _ingest(stores: list[ConvenienceStore], region_code: str, observed_on: date) -> int:
    interactor = ConvenienceSnapshotInteractor(
        repository=SqlAlchemyConvenienceStoreRepository(), gateway=FakeGateway(stores)
    )
    return interactor.ingest(region_code, observed_on)


def test_first_load_sets_first_and_last_seen():
    _cleanup()
    region = _region_code()
    processed = _ingest([_store(1, region), _store(2, region)], region, date(2026, 9, 7))
    assert processed == 2
    for first_seen, last_seen, _, _ in _rows().values():
        assert (first_seen, last_seen) == (date(2026, 9, 7), date(2026, 9, 7))
    _cleanup()


def test_reingest_is_idempotent_and_updates_source_fields():
    _cleanup()
    region = _region_code()
    _ingest([_store(1, region)], region, date(2026, 9, 7))
    # 같은 관측일 재실행 (멱등) + 원천 상호 변경 반영
    processed = _ingest([_store(1, region, name="지에스25시험점")], region, date(2026, 9, 7))
    assert processed == 1
    first_seen, last_seen, name, _ = _rows()[f"{_TEST_PREFIX}1"]
    assert (first_seen, last_seen) == (date(2026, 9, 7), date(2026, 9, 7))
    assert name == "지에스25시험점"
    _cleanup()


def test_missing_store_keeps_stale_last_seen():
    """스냅샷 소실 = last_seen_on 정지 (broker 전례의 '사라짐=폐점 추정' 후속 분석 근거)."""
    _cleanup()
    region = _region_code()
    _ingest([_store(1, region), _store(2, region)], region, date(2026, 9, 7))

    # 다음 스냅샷에서 2번 소실 — 1번만 관측 갱신, 2번은 first/last_seen 그대로
    _ingest([_store(1, region)], region, date(2026, 9, 14))
    rows = _rows()
    assert rows[f"{_TEST_PREFIX}1"][:2] == (date(2026, 9, 7), date(2026, 9, 14))
    assert rows[f"{_TEST_PREFIX}2"][:2] == (date(2026, 9, 7), date(2026, 9, 7))

    # 재등장 — last_seen만 전진, first_seen(최초 관측)은 보존
    _ingest([_store(1, region), _store(2, region)], region, date(2026, 9, 21))
    assert _rows()[f"{_TEST_PREFIX}2"][:2] == (date(2026, 9, 7), date(2026, 9, 21))
    _cleanup()


def test_batch_duplicate_store_id_deduped():
    _cleanup()
    region = _region_code()
    processed = _ingest([_store(1, region), _store(1, region)], region, date(2026, 9, 7))
    assert processed == 1
    _cleanup()
