"""academy ingest 검증 — store 업서트 + academy_course 재적재(delete+insert) 멱등."""

from collections.abc import Iterator
from datetime import date, datetime

from sqlalchemy import delete, select

from apps.store.adapter.outbound.orms.academy_course_orm import AcademyCourseOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.adapter.outbound.repositories.academy_course_repository import (
    SqlAlchemyAcademyCourseRepository,
)
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.dtos.academy_course_dto import AcademyRecord
from apps.store.app.ports.output.academy_course_port import AcademyGatewayPort
from apps.store.app.use_cases.academy_course_interactor import AcademyCourseInteractor
from apps.store.domain.entities.academy_course_entity import AcademyCourse
from apps.store.domain.entities.store_entity import Store

_TEST_PREFIX = "test-academy-"


def _record(n: int, course_names: list[str]) -> AcademyRecord:
    store_id = f"{_TEST_PREFIX}{n}"
    return AcademyRecord(
        store=Store(
            store_id=store_id,
            name=f"학원 {n}",
            industry_id="academy",
            district_code="11110",
            open_date=date(2020, 1, n),
            close_date=None,
            status_code="open",
            status_name="개원",
            lat=None,
            lng=None,
            source_updated_at=datetime(2026, 9, 7),
            subcategory_id="academy_exam",
        ),
        courses=[
            AcademyCourse(
                course_id=f"{store_id}:{i}",
                store_id=store_id,
                course_name=name,
                tuition_fee=100000 * i,
            )
            for i, name in enumerate(course_names, start=1)
        ],
    )


class FakeGateway(AcademyGatewayPort):
    def __init__(self, records: list[AcademyRecord]) -> None:
        self._records = records

    def iter_academies(self) -> Iterator[AcademyRecord]:
        yield from self._records


def _cleanup():
    from core.matrix.grid_oracle_database_manager import session_scope

    with session_scope() as session:
        session.execute(
            delete(AcademyCourseOrm).where(AcademyCourseOrm.store_id.like(f"{_TEST_PREFIX}%"))
        )
        session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_TEST_PREFIX}%")))


def _interactor(records: list[AcademyRecord]) -> AcademyCourseInteractor:
    return AcademyCourseInteractor(
        store_repository=SqlAlchemyStoreRepository(),
        course_repository=SqlAlchemyAcademyCourseRepository(),
        gateway=FakeGateway(records),
    )


def test_ingest_loads_stores_and_courses():
    _cleanup()
    stores, courses = _interactor([_record(1, ["수학"]), _record(2, ["영어", "국어"])]).ingest()
    assert (stores, courses) == (2, 3)
    _cleanup()


def test_reingest_replaces_courses_idempotently():
    from core.matrix.grid_oracle_database_manager import session_scope

    _cleanup()
    _interactor([_record(1, ["수학", "과학"])]).ingest()
    # 재수집에서 과정이 1건으로 바뀐 상황 — delete+insert라 이전 잔재가 남지 않아야 한다
    stores, courses = _interactor([_record(1, ["수학"])]).ingest()
    assert (stores, courses) == (1, 1)

    with session_scope() as session:
        rows = session.execute(
            select(AcademyCourseOrm.course_name).where(
                AcademyCourseOrm.store_id == f"{_TEST_PREFIX}1"
            )
        ).scalars().all()
    assert rows == ["수학"]
    _cleanup()
