"""convenience 조회 검증 — myself 배선·마커 목록·행정동 브랜드 요약 계약·404 에러 바디 (Fake 포트)."""

from datetime import date

from fastapi.testclient import TestClient

from apps.convenience.app.ports.output.convenience_store_port import (
    ConvenienceStoreQueryRepositoryPort,
    RegionCatalogPort,
)
from apps.convenience.app.use_cases.convenience_store_interactor import (
    ConvenienceStoreQueryInteractor,
)
from apps.convenience.dependencies.convenience_dependencies import (
    get_convenience_store_query_use_case,
)
from apps.convenience.domain.entities.convenience_store_entity import (
    ConvenienceRegionSummary,
    ConvenienceStore,
)
from main import app

_REGION = "1168064000"


def _store(store_id: str, brand: str | None = "CU", lat: float | None = 37.5) -> ConvenienceStore:
    return ConvenienceStore(
        store_id=store_id,
        name=f"편의점 {store_id}",
        branch_name=None,
        brand=brand,
        region_code=_REGION,
        lat=lat,
        lng=None if lat is None else 127.03,
        road_address="서울특별시 강남구 테헤란로 1",
        jibun_address=None,
        source_stdr_ym="202606",
    )


class FakeRegionCatalog(RegionCatalogPort):
    def exists(self, region_code: str) -> bool:
        return region_code == _REGION


class FakeRepository(ConvenienceStoreQueryRepositoryPort):
    def list_current(self, region_code: str) -> list[ConvenienceStore]:
        return [_store("s1", "GS25"), _store("s2", None), _store("s3", "GS25", lat=None)]


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _client() -> TestClient:
    app.dependency_overrides[get_convenience_store_query_use_case] = lambda: (
        ConvenienceStoreQueryInteractor(
            repository=FakeRepository(), region_catalog=FakeRegionCatalog()
        )
    )
    return TestClient(app)


def test_convenience_store_myself_wiring_returns_200():
    response = TestClient(app).get("/convenience-stores/myself")
    assert response.status_code == 200
    assert response.json()["store_id"] == "myself"


def test_list_stores_returns_marker_contract_with_coords_only():
    response = _client().get("/convenience-stores", params={"region": _REGION})
    assert response.status_code == 200
    body = response.json()
    assert [s["store_id"] for s in body] == ["s1", "s2"]  # 좌표 없는 s3 제외
    assert body[0] == {
        "store_id": "s1",
        "name": "편의점 s1",
        "branch_name": None,
        "brand": "GS25",
        "lat": 37.5,
        "lng": 127.03,
        "road_address": "서울특별시 강남구 테헤란로 1",
    }


def test_summary_counts_all_current_stores_by_brand():
    response = _client().get("/convenience-stores/summary", params={"region": _REGION})
    assert response.status_code == 200
    assert response.json() == {
        "region_code": _REGION,
        "store_count": 3,
        "brands": [{"brand": "GS25", "count": 2}, {"brand": None, "count": 1}],
        "source_stdr_ym": "202606",
    }


def test_unknown_region_returns_404_error_body():
    client = _client()
    for path in ("/convenience-stores", "/convenience-stores/summary"):
        response = client.get(path, params={"region": "0000000000"})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_region_summary_orders_brands_by_count_and_unknown_last():
    stores = [_store("a", "CU"), _store("b", None), _store("c", None), _store("d", None),
              _store("e", "GS25"), _store("f", "GS25"), _store("g", "이마트24"), _store("h", "CU")]
    summary = ConvenienceRegionSummary.of(_REGION, stores)
    # 건수 내림차순·동수는 브랜드명 순, 미확인(None)은 건수와 무관하게 맨 뒤
    assert [(b.brand, b.count) for b in summary.brands] == [
        ("CU", 2), ("GS25", 2), ("이마트24", 1), (None, 3)
    ]


def test_region_summary_of_empty():
    summary = ConvenienceRegionSummary.of(_REGION, [])
    assert (summary.store_count, summary.brands, summary.source_stdr_ym) == (0, (), None)
