"""childcare 조회 검증 — myself 배선·마커 목록·행정동 요약 계약·404 에러 바디 (Fake 포트)."""

from datetime import date

from fastapi.testclient import TestClient

from apps.childcare.app.ports.output.childcare_center_port import (
    ChildcareCenterQueryRepositoryPort,
    RegionCatalogPort,
)
from apps.childcare.app.ports.output.childcare_center_stat_port import (
    ChildcareCenterStatRepositoryPort,
)
from apps.childcare.app.use_cases.childcare_center_interactor import (
    ChildcareCenterQueryInteractor,
)
from apps.childcare.app.use_cases.childcare_center_stat_interactor import (
    ChildcareCenterStatInteractor,
)
from apps.childcare.dependencies.childcare_dependencies import (
    get_childcare_center_query_use_case,
    get_childcare_center_stat_use_case,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import (
    ChildcareCenterStat,
    ChildcareRegionSummary,
)
from main import app

_REGION = "1111051500"


def _stat(capacity: int = 39, child_count: int = 25, waiting: int | None = 20) -> ChildcareCenterStat:
    return ChildcareCenterStat(
        base_date=date(2026, 9, 17),
        capacity=capacity,
        child_count=child_count,
        waiting_count=waiting,
        class_count=7,
        staff_count=10,
    )


def _center(center_id: str) -> ChildcareCenter:
    return ChildcareCenter(
        center_id=center_id,
        name=f"시험어린이집 {center_id}",
        type_name="국공립",
        status_name="정상",
        district_code="11110",
        address="서울특별시 종로구 시험로 1",
        zipcode=None,
        tel=None,
        lat=37.58,
        lng=126.98,
        approved_on=date(1995, 6, 23),
        paused_from=None,
        paused_until=None,
        abolished_on=None,
        stat=_stat(),
    )


class FakeRegionCatalog(RegionCatalogPort):
    def exists(self, region_code: str) -> bool:
        return region_code == _REGION


class FakeCenterRepository(ChildcareCenterQueryRepositoryPort):
    def list_operating(self, region_code: str) -> list[ChildcareCenter]:
        return [_center("c1"), _center("c2")] if region_code == _REGION else []


class FakeStatRepository(ChildcareCenterStatRepositoryPort):
    def list_latest(self, region_code: str) -> list[ChildcareCenterStat]:
        return [_stat(40, 30, 5), _stat(60, 30, None)]


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _client() -> TestClient:
    app.dependency_overrides[get_childcare_center_query_use_case] = lambda: (
        ChildcareCenterQueryInteractor(
            repository=FakeCenterRepository(), region_catalog=FakeRegionCatalog()
        )
    )
    app.dependency_overrides[get_childcare_center_stat_use_case] = lambda: (
        ChildcareCenterStatInteractor(
            repository=FakeStatRepository(), region_catalog=FakeRegionCatalog()
        )
    )
    return TestClient(app)


def test_childcare_center_myself_wiring_returns_200():
    response = TestClient(app).get("/childcare-centers/myself")
    assert response.status_code == 200
    assert response.json()["center_id"] == "myself"


def test_childcare_center_stat_myself_wiring_returns_200():
    response = TestClient(app).get("/childcare-center-stats/myself")
    assert response.status_code == 200
    assert response.json()["region_code"] == "myself"


def test_list_centers_returns_marker_contract():
    response = _client().get("/childcare-centers", params={"region": _REGION})
    assert response.status_code == 200
    first = response.json()[0]
    assert first == {
        "center_id": "c1",
        "name": "시험어린이집 c1",
        "type_name": "국공립",
        "status_name": "정상",
        "lat": 37.58,
        "lng": 126.98,
        "base_date": "2026-09-17",
        "capacity": 39,
        "child_count": 25,
        "waiting_count": 20,
    }


def test_summary_returns_region_aggregate():
    response = _client().get("/childcare-center-stats/summary", params={"region": _REGION})
    assert response.status_code == 200
    assert response.json() == {
        "region_code": _REGION,
        "base_date": "2026-09-17",
        "center_count": 2,
        "capacity": 100,
        "child_count": 60,
        "occupancy_rate": 0.6,
        "waiting_count": 5,
    }


def test_unknown_region_returns_404_error_body():
    client = _client()
    for path in ("/childcare-centers", "/childcare-center-stats/summary"):
        response = client.get(path, params={"region": "0000000000"})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_region_summary_of_empty_has_no_rates():
    summary = ChildcareRegionSummary.of(_REGION, [])
    assert (summary.center_count, summary.capacity, summary.child_count) == (0, 0, 0)
    assert (summary.occupancy_rate, summary.waiting_count, summary.base_date) == (None, None, None)


def test_region_summary_waiting_is_none_when_all_blank():
    summary = ChildcareRegionSummary.of(_REGION, [_stat(waiting=None), _stat(waiting=None)])
    assert summary.waiting_count is None
    assert summary.occupancy_rate == round(50 / 78, 4)
