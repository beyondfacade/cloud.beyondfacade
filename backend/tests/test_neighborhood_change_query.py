"""상권 변화 지표 조회 검증 — 단계구분도 값 목록·최신 분기 기본값·미지원 metric (Fake 포트)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.neighborhood.adapter.inbound.api.v1.region_commerce_change_router import (
    get_region_commerce_change_query_use_case,
    router,
)
from apps.neighborhood.app.ports.output.region_commerce_change_query_port import (
    RegionCommerceChangeQueryPort,
)
from apps.neighborhood.app.use_cases.region_commerce_change_query_interactor import (
    RegionCommerceChangeQueryInteractor,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import (
    RegionCommerceChange,
)
from apps.neighborhood.domain.errors import MetricNotFoundError


def _row(region_code: str, year_quarter: str, operating_months: float | None) -> RegionCommerceChange:
    return RegionCommerceChange(
        adstrd_code=region_code[:8],
        year_quarter=year_quarter,
        change_code="LL",
        change_name="다이나믹",
        operating_months=operating_months,
        closed_months=48.0,
        region_code=region_code,
    )


class FakeQueryPort(RegionCommerceChangeQueryPort):
    def __init__(self, rows: list[RegionCommerceChange]) -> None:
        self.rows = rows
        self.requested_quarter: str | None = None

    def latest_quarter(self) -> str | None:
        quarters = [r.year_quarter for r in self.rows]
        return max(quarters) if quarters else None

    def list_by_quarter(self, year_quarter: str) -> list[RegionCommerceChange]:
        self.requested_quarter = year_quarter
        return sorted(
            (r for r in self.rows if r.year_quarter == year_quarter),
            key=lambda r: r.region_code or "",
        )


_ROWS = [
    _row("1168064000", "20262", 110.0),
    _row("1168051000", "20262", 95.5),
    _row("1168010100", "20262", None),  # 원천 공란 — 0으로 읽으면 안 된다
    _row("1168064000", "20253", 104.0),
]


@pytest.fixture
def port() -> FakeQueryPort:
    return FakeQueryPort(list(_ROWS))


@pytest.fixture
def client(port: FakeQueryPort) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_region_commerce_change_query_use_case] = (
        lambda: RegionCommerceChangeQueryInteractor(port)
    )
    return TestClient(app)


def test_myself는_배선만_확인한다(client):
    response = client.get("/commerce-changes/myself")

    assert response.status_code == 200
    assert response.json()["region_code"] == "myself"


def test_분기를_생략하면_최신_분기를_쓴다(client, port):
    response = client.get("/commerce-changes", params={"metric": "operating_months"})

    assert response.status_code == 200
    assert port.requested_quarter == "20262"


def test_단계구분도_응답은_region_code와_value_쌍이다(client):
    body = client.get(
        "/commerce-changes", params={"metric": "operating_months", "year_quarter": "20262"}
    ).json()

    assert all(set(row) == {"region_code", "value"} for row in body)
    assert {row["region_code"] for row in body} == {"1168051000", "1168064000"}
    assert next(r["value"] for r in body if r["region_code"] == "1168064000") == 110.0


def test_값이_없는_동은_행을_만들지_않는다(client):
    # 원천 공란을 0으로 내보내면 "가장 빨리 닫는 동네"로 색칠된다
    body = client.get(
        "/commerce-changes", params={"metric": "operating_months", "year_quarter": "20262"}
    ).json()

    assert "1168010100" not in {row["region_code"] for row in body}


def test_미지원_metric은_500이_아니라_404다(client):
    response = client.get("/commerce-changes", params={"metric": "nonexistent"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "METRIC_NOT_FOUND"


def test_인터랙터는_미지원_metric에_도메인_예외를_던진다(port):
    interactor = RegionCommerceChangeQueryInteractor(port)

    with pytest.raises(MetricNotFoundError):
        interactor.list_metric_values("nonexistent", None)


def test_적재_전이면_빈_목록이다():
    interactor = RegionCommerceChangeQueryInteractor(FakeQueryPort([]))

    assert interactor.list_metric_values("operating_months", None) == []
