"""shock ingest 검증 — Fake 소스(경계 모킹) + 실제 Repository/DB 업서트 멱등·업종 조인 무결성."""

from datetime import date

from sqlalchemy import delete, select

from apps.shock.adapter.outbound.orms.shock_event_industry_orm import (
    ShockEventIndustryOrm,
)
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.ports.output.shock_event_port import ShockEventSourcePort
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor
from apps.shock.domain.entities.shock_event_entity import IndustryImpact, ShockEvent
from apps.shock.domain.value_objects.shock_layer import Severity, ShockLayer
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-shock-"


def _event(n: int, impacts: list[IndustryImpact] | None = None) -> ShockEvent:
    return ShockEvent(
        event_id=f"{_TEST_PREFIX}{n}",
        layer=ShockLayer.POLICY,
        name=f"충격 {n}",
        start_date=date(2020, 3, 22),
        end_date=date(2020, 5, 5),
        scope="전국",
        source="테스트 출처",
        industry_impacts=impacts
        if impacts is not None
        else [IndustryImpact("karaoke", Severity.CRITICAL)],
    )


class FakeSource(ShockEventSourcePort):
    def __init__(self, events: list[ShockEvent]) -> None:
        self._events = events

    def fetch_events(self) -> list[ShockEvent]:
        return self._events


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(ShockEventIndustryOrm).where(
                ShockEventIndustryOrm.event_id.like(f"{_TEST_PREFIX}%")
            )
        )
        session.execute(
            delete(ShockEventOrm).where(ShockEventOrm.event_id.like(f"{_TEST_PREFIX}%"))
        )


def test_ingest_upsert_is_idempotent():
    _cleanup()
    repository = SqlAlchemyShockEventRepository()
    interactor = ShockEventInteractor(
        repository=repository, source=FakeSource([_event(1), _event(2)])
    )
    assert interactor.ingest() == (2, 0)
    assert interactor.ingest() == (0, 0)  # 재실행 — 내용 동일이면 무변경
    _cleanup()


def test_upsert_replaces_industry_impacts():
    _cleanup()
    repository = SqlAlchemyShockEventRepository()
    repository.upsert([_event(1, impacts=[IndustryImpact("karaoke", Severity.CRITICAL)])])
    # 영향 업종이 바뀌면 조인 행이 교체된다 (잔존 행 없음)
    inserted, updated = repository.upsert(
        [_event(1, impacts=[IndustryImpact("cafe", Severity.HIGH)])]
    )
    assert (inserted, updated) == (0, 1)
    with session_scope() as session:
        rows = list(
            session.execute(
                select(ShockEventIndustryOrm.industry_id).where(
                    ShockEventIndustryOrm.event_id == f"{_TEST_PREFIX}1"
                )
            ).scalars()
        )
    assert rows == ["cafe"]
    _cleanup()


def test_list_events_filters_by_industry():
    _cleanup()
    repository = SqlAlchemyShockEventRepository()
    repository.upsert(
        [
            _event(1, impacts=[IndustryImpact("karaoke", Severity.CRITICAL)]),
            _event(2, impacts=[IndustryImpact("cafe", Severity.MEDIUM)]),
        ]
    )
    karaoke_ids = {
        e.event_id
        for e in repository.list_events(industry_id="karaoke", limit=100)
        if e.event_id.startswith(_TEST_PREFIX)
    }
    assert karaoke_ids == {f"{_TEST_PREFIX}1"}
    listed = [
        e for e in repository.list_events(industry_id=None, limit=1000)
        if e.event_id.startswith(_TEST_PREFIX)
    ]
    assert {e.event_id for e in listed} == {f"{_TEST_PREFIX}1", f"{_TEST_PREFIX}2"}
    assert listed[0].industry_impacts  # 목록에도 업종 영향 동봉
    _cleanup()
