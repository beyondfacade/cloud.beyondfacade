"""④지역 이벤트 적재·조회 — Fake 원천·위치판정(경계 모킹) + 실제 Repository/DB.

정책 이벤트용 기존 목록(list_events — 리포트 '외부 충격' 공통 폴백)에 지역 이벤트가 섞이지 않는지도 고정한다.
"""

from datetime import date

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.adapter.outbound.orms.shock_event_region_orm import ShockEventRegionOrm
from apps.shock.adapter.outbound.repositories.shock_event_region_repository import (
    SqlAlchemyShockEventRegionRepository,
)
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.dtos.shock_event_region_dto import LocatedEvent
from apps.shock.app.ports.output.shock_event_region_port import (
    RegionalEventSourcePort,
    RegionLocatorPort,
)
from apps.shock.app.use_cases.shock_event_region_interactor import (
    ShockEventRegionInteractor,
)
from apps.shock.domain.services.regional_events import apartment_event
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "regional-apt-movein-TEST"


class FakeSource(RegionalEventSourcePort):
    def __init__(self, located: list[LocatedEvent]) -> None:
        self._located = located

    def fetch_located_events(self) -> list[LocatedEvent]:
        return self._located


class FakeLocator(RegionLocatorPort):
    """lat 37.5 → 첫 행정동, 그 밖은 경계 밖(None)."""

    def __init__(self, region_code: str) -> None:
        self._region_code = region_code

    def locate(self, lat: float, lng: float) -> str | None:
        return self._region_code if lat == 37.5 else None


def _region_codes() -> list[str]:
    with session_scope() as session:
        return list(
            session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(2)).scalars()
        )


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(delete(ShockEventRegionOrm).where(ShockEventRegionOrm.event_id.like(f"{_PREFIX}%")))
        session.execute(delete(ShockEventOrm).where(ShockEventOrm.event_id.like(f"{_PREFIX}%")))


def _apt(n: int, year: int) -> LocatedEvent:
    event = apartment_event(f"TEST{n}", f"테스트단지{n}", 1500, date(year, 3, 1))
    return LocatedEvent(event=event, lat=37.5, lng=127.0)


def _interactor(region_code: str) -> ShockEventRegionInteractor:
    return ShockEventRegionInteractor(
        events=SqlAlchemyShockEventRepository(),
        links=SqlAlchemyShockEventRegionRepository(),
        locator=FakeLocator(region_code),
    )


def test_ingest_links_located_events_skips_unlocated_and_is_idempotent():
    _cleanup()
    region_code = _region_codes()[0]
    no_coordinate = LocatedEvent(event=_apt(3, 2021).event, lat=None, lng=None)
    outside = LocatedEvent(event=_apt(4, 2021).event, lat=36.0, lng=127.0)
    source = FakeSource([_apt(1, 2019), _apt(2, 2024), no_coordinate, outside])

    result = _interactor(region_code).ingest(source)
    assert [(e.event_id, code) for e, code in result.linked] == [
        (f"{_PREFIX}1", region_code),
        (f"{_PREFIX}2", region_code),
    ]
    assert [e.event_id for e in result.no_location] == [f"{_PREFIX}3"]
    assert [e.event_id for e in result.no_region] == [f"{_PREFIX}4"]
    assert (result.inserted, result.updated) == (2, 0)

    again = _interactor(region_code).ingest(source)  # 재실행 — 무변경
    assert (again.inserted, again.updated, len(again.linked)) == (0, 0, 2)

    listed = _interactor(region_code).list_for_region(region_code)
    ours = [e.event_id for e in listed if e.event_id.startswith(_PREFIX)]
    assert ours == [f"{_PREFIX}2", f"{_PREFIX}1"]  # 최근 것 먼저
    _cleanup()


def test_relocated_event_moves_its_region_link():
    _cleanup()
    first, second = _region_codes()
    _interactor(first).ingest(FakeSource([_apt(1, 2020)]))
    _interactor(second).ingest(FakeSource([_apt(1, 2020)]))  # 재지오코딩으로 동이 바뀐 경우
    def ours(region_code: str) -> list[str]:
        listed = _interactor(region_code).list_for_region(region_code)
        return [e.event_id for e in listed if e.event_id.startswith(_PREFIX)]

    assert ours(first) == []
    assert ours(second) == [f"{_PREFIX}1"]
    _cleanup()


def test_regional_events_stay_out_of_policy_shock_list():
    _cleanup()
    _interactor(_region_codes()[0]).ingest(FakeSource([_apt(1, 2019)]))
    listed = SqlAlchemyShockEventRepository().list_events(industry_id=None, limit=10_000)
    assert not any(e.event_id.startswith(_PREFIX) for e in listed)
    _cleanup()
