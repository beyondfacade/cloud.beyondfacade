"""시간대 어긋남 라우터 검증 — 배선(myself) · 분기 생략 시 최신 · 분기 지정 · 6행 순서 · 404 · 422 (Fake 포트).

상세 계약(`map-metric-contract` §3-2)의 첫 hour_gap 구현이다. 응답은 동×업종×분기 한 객체에 6구간이 담긴다.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.metric.adapter.inbound.api.v1.region_industry_hour_gap_router import (
    get_region_industry_hour_gap_use_case,
    router,
)
from apps.metric.app.ports.output.region_industry_hour_gap_port import (
    RegionFootfallHourPort,
    RegionIndustryHourGapRepositoryPort,
    RegionIndustryHourSalesPort,
)
from apps.metric.app.use_cases.region_industry_hour_gap_interactor import (
    RegionIndustryHourGapInteractor,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)
from apps.metric.domain.value_objects.hour_band import HOUR_BANDS

_REGION, _INDUSTRY = "1168064000", "cafe"


def _bands(year_quarter: str, peak: str) -> list[RegionIndustryHourGap]:
    """유동은 균등(1.0), 매출은 `peak` 구간만 2.0 — 어긋남 부호가 그 구간에서만 양수가 된다."""
    return [
        RegionIndustryHourGap(
            region_code=_REGION,
            industry_id=_INDUSTRY,
            year_quarter=year_quarter,
            hour_band=band,
            footfall_intensity=1.0,
            sales_intensity=2.0 if band == peak else 0.8,
            gap=(2.0 if band == peak else 0.8) - 1.0,
        )
        for band in HOUR_BANDS
    ]


class FakeRepository(RegionIndustryHourGapRepositoryPort):
    def __init__(self, rows: list[RegionIndustryHourGap]) -> None:
        self.rows = {(r.region_code, r.industry_id, r.year_quarter, r.hour_band): r for r in rows}

    def upsert(self, gaps):
        return 0

    def list_bands(self, region_code, industry_id, year_quarter):
        # 구간 어휘 순 — 문자열 정렬과 일치하지만 단일 원천을 쓴다
        order = {band: i for i, band in enumerate(HOUR_BANDS)}
        return sorted(
            (r for k, r in self.rows.items() if k[:3] == (region_code, industry_id, year_quarter)),
            key=lambda r: order[r.hour_band],
        )

    def latest_quarter(self, region_code, industry_id):
        quarters = [k[2] for k in self.rows if k[:2] == (region_code, industry_id)]
        return max(quarters) if quarters else None


class UnusedFootfall(RegionFootfallHourPort):
    def hour_values(self, quarters):
        raise AssertionError("조회 경로는 원자료를 읽지 않는다")


class UnusedSales(RegionIndustryHourSalesPort):
    def hour_sales(self, quarters):
        raise AssertionError("조회 경로는 원자료를 읽지 않는다")


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    # 20253은 저녁 정점, 20254(최신)는 점심 정점 — 분기 선택이 틀리면 정점이 바뀐다
    repository = FakeRepository([*_bands("20253", "17_21"), *_bands("20254", "11_14")])
    interactor = RegionIndustryHourGapInteractor(
        repository=repository, footfall=UnusedFootfall(), sales=UnusedSales()
    )
    app.dependency_overrides[get_region_industry_hour_gap_use_case] = lambda: interactor
    return TestClient(app)


def _peak(body: dict) -> str:
    return max(body["bands"], key=lambda b: b["sales_intensity"])["hour_band"]


def test_myself는_배선만_확인한다(client):
    response = client.get("/hour-gaps/myself")

    assert response.status_code == 200
    body = response.json()
    assert body["region_code"] == "myself"
    assert body["bands"] and set(body["bands"][0]) == {
        "hour_band", "footfall_intensity", "sales_intensity", "gap"
    }


def test_분기를_생략하면_그_조합의_최신_분기를_준다(client):
    response = client.get("/hour-gaps", params={"region": _REGION, "industry": _INDUSTRY})

    assert response.status_code == 200
    body = response.json()
    assert body["year_quarter"] == "20254"  # 프로필(20262)이 아니라 이 조합의 최신이다
    assert _peak(body) == "11_14"


def test_분기를_지정하면_그_분기를_준다(client):
    body = client.get(
        "/hour-gaps", params={"region": _REGION, "industry": _INDUSTRY, "year_quarter": "20253"}
    ).json()

    assert body["year_quarter"] == "20253"
    assert _peak(body) == "17_21"


def test_응답은_한_객체에_6구간이_시간_순으로_담긴다(client):
    body = client.get("/hour-gaps", params={"region": _REGION, "industry": _INDUSTRY}).json()

    assert (body["region_code"], body["industry_id"]) == (_REGION, _INDUSTRY)
    assert [b["hour_band"] for b in body["bands"]] == list(HOUR_BANDS)
    assert all(b["gap"] == pytest.approx(b["sales_intensity"] - b["footfall_intensity"]) for b in body["bands"])


def test_매출이_없는_조합은_404_HOUR_GAP_NOT_FOUND(client):
    response = client.get("/hour-gaps", params={"region": _REGION, "industry": "childcare"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HOUR_GAP_NOT_FOUND"


def test_없는_분기도_404다(client):
    response = client.get(
        "/hour-gaps", params={"region": _REGION, "industry": _INDUSTRY, "year_quarter": "20211"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HOUR_GAP_NOT_FOUND"


def test_region이나_industry가_빠지면_422다(client):
    assert client.get("/hour-gaps", params={"industry": _INDUSTRY}).status_code == 422
    assert client.get("/hour-gaps", params={"region": _REGION}).status_code == 422
