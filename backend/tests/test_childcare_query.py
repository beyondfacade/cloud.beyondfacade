"""childcare 조회 검증 — myself 배선·마커 목록·행정동 요약 집계·404 에러 바디 (Fake 포트)."""

from datetime import date

from fastapi.testclient import TestClient

from apps.childcare.app.ports.output.childcare_center_port import (
    ChildcareCenterQueryRepositoryPort,
    RegionCatalogPort,
)
from apps.childcare.app.use_cases.childcare_center_interactor import (
    ChildcareCenterQueryInteractor,
)
from apps.childcare.dependencies.childcare_dependencies import (
    get_childcare_center_query_use_case,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
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


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _client() -> TestClient:
    app.dependency_overrides[get_childcare_center_query_use_case] = lambda: (
        ChildcareCenterQueryInteractor(
            repository=FakeCenterRepository(), region_catalog=FakeRegionCatalog()
        )
    )
    return TestClient(app)


def test_childcare_center_myself_wiring_returns_200():
    response = TestClient(app).get("/childcare-centers/myself")
    assert response.status_code == 200
    assert response.json()["center_id"] == "myself"


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


def test_unknown_region_returns_404_error_body():
    response = _client().get("/childcare-centers", params={"region": "0000000000"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_NOT_FOUND"
