"""동네 프로필 라우터 검증 — 배선(myself) · 최신 분기 기본값 · 분기 지정 · 404 (Fake 포트)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.metric.adapter.inbound.api.v1.region_profile_router import (
    get_region_profile_use_case,
    router,
)
from apps.metric.app.ports.output.region_profile_port import (
    NeighborhoodObservationPort,
    RegionProfileRepositoryPort,
)
from apps.metric.app.use_cases.region_profile_interactor import RegionProfileInteractor
from apps.metric.domain.entities.region_profile_entity import RegionProfile


def _profile(year_quarter: str, **overrides) -> RegionProfile:
    base = dict(
        region_code="1168064000",
        year_quarter=year_quarter,
        neighborhood_type="office",
        type_reason="직장인구가 상주인구의 5.9배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다.",
        time_label="day",
        peak_block="day",
        trough_block="night",
        worker_resident_ratio=5.93,
        weekend_index=0.81,
        night_index=0.639,
        footfall_20s_share=0.225,
        fnb_share=0.016,
        facility_total=195,
        resident_total=34082,
    )
    return RegionProfile(**{**base, **overrides})


class FakeRepository(RegionProfileRepositoryPort):
    def __init__(self, profiles: list[RegionProfile]) -> None:
        self.rows = {(p.region_code, p.year_quarter): p for p in profiles}

    def upsert(self, profiles: list[RegionProfile]) -> int:
        return 0

    def find(self, region_code: str, year_quarter: str) -> RegionProfile | None:
        return self.rows.get((region_code, year_quarter))

    def find_latest(self, region_code: str) -> RegionProfile | None:
        candidates = [p for p in self.rows.values() if p.region_code == region_code]
        return max(candidates, key=lambda p: p.year_quarter) if candidates else None

    def latest_quarter(self) -> str | None:
        quarters = [p.year_quarter for p in self.rows.values()]
        return max(quarters) if quarters else None

    def list_by_quarter(self, year_quarter: str) -> list[RegionProfile]:
        return sorted(
            (p for p in self.rows.values() if p.year_quarter == year_quarter),
            key=lambda p: p.region_code,
        )


class UnusedObservations(NeighborhoodObservationPort):
    def quarter_observations(self, quarters):
        raise AssertionError("조회 경로는 원자료를 읽지 않는다")


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    interactor = RegionProfileInteractor(
        repository=FakeRepository(
            [
                _profile("20253"),
                _profile("20261", neighborhood_type="mixed", worker_resident_ratio=None),
            ]
        ),
        observations=UnusedObservations(),
    )
    app.dependency_overrides[get_region_profile_use_case] = lambda: interactor
    return TestClient(app)


def test_myself는_배선만_확인한다(client):
    response = client.get("/profiles/myself")

    assert response.status_code == 200
    assert response.json()["region_code"] == "myself"


def test_분기를_생략하면_가장_최근_분기를_준다(client):
    response = client.get("/profiles/1168064000")

    assert response.status_code == 200
    body = response.json()
    assert body["year_quarter"] == "20261"
    assert body["neighborhood_type"] == "mixed"


def test_분기를_지정하면_그_분기를_준다(client):
    response = client.get("/profiles/1168064000", params={"year_quarter": "20253"})

    assert response.status_code == 200
    assert response.json()["year_quarter"] == "20253"
    assert response.json()["neighborhood_type"] == "office"


def test_판정_근거_수치가_판정과_함께_온다(client):
    body = client.get("/profiles/1168064000", params={"year_quarter": "20253"}).json()

    assert body["worker_resident_ratio"] == pytest.approx(5.93)
    assert body["night_index"] == pytest.approx(0.639)
    assert "서울 상위 10%" in body["type_reason"]
    assert (body["peak_block"], body["trough_block"]) == ("day", "night")


def test_없는_동은_404_REGION_PROFILE_NOT_FOUND(client):
    response = client.get("/profiles/9999999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_PROFILE_NOT_FOUND"


def test_없는_분기도_404다(client):
    response = client.get("/profiles/1168064000", params={"year_quarter": "19991"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REGION_PROFILE_NOT_FOUND"


# --- 단계구분도 목록 (설계서 `2026-09-23-map-metric-contract.md` §3-1) ---


def test_지원하는_지표는_region_code와_value_쌍_목록을_준다(client):
    response = client.get("/profiles", params={"metric": "night_index", "year_quarter": "20253"})

    assert response.status_code == 200
    body = response.json()
    assert all(set(row) == {"region_code", "value"} for row in body)
    assert body == [{"region_code": "1168064000", "value": pytest.approx(0.639)}]


def test_파생_지표_7종이_전부_열려_있다(client):
    # region_profile_quarter의 숫자 컬럼 전부 — extractor 테이블 한 줄씩이다
    for metric in (
        "worker_resident_ratio",
        "weekend_index",
        "night_index",
        "footfall_20s_share",
        "fnb_share",
        "facility_total",
        "resident_total",
    ):
        response = client.get("/profiles", params={"metric": metric, "year_quarter": "20253"})
        assert response.status_code == 200, metric
        assert response.json(), metric


def test_분기를_생략하면_최신_분기를_쓴다(client):
    최신 = client.get("/profiles", params={"metric": "night_index"}).json()
    지정 = client.get("/profiles", params={"metric": "night_index", "year_quarter": "20261"}).json()

    assert 최신 == 지정


def test_값이_없는_동은_행을_만들지_않는다(client):
    # 직장인구 결측 11개 동을 0으로 내보내면 지도가 "직장인이 없는 동네"로 색칠한다
    body = client.get(
        "/profiles", params={"metric": "worker_resident_ratio", "year_quarter": "20261"}
    ).json()

    assert body == []


def test_미지원_metric은_500이_아니라_404다(client):
    response = client.get("/profiles", params={"metric": "type_reason"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "METRIC_NOT_FOUND"


def test_적재_전이면_빈_목록이다():
    interactor = RegionProfileInteractor(
        repository=FakeRepository([]), observations=UnusedObservations()
    )

    assert interactor.list_metric_values("night_index", None) == []
