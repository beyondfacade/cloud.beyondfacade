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
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_query_port import (
    SeoulCommerceChangeBaselineQueryPort,
)
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
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

    def find(self, region_code: str, year_quarter: str) -> RegionCommerceChange | None:
        return next(
            (r for r in self.rows if r.region_code == region_code and r.year_quarter == year_quarter),
            None,
        )

    def find_latest(self, region_code: str) -> RegionCommerceChange | None:
        candidates = [r for r in self.rows if r.region_code == region_code]
        return max(candidates, key=lambda r: r.year_quarter) if candidates else None


class FakeBaselinePort(SeoulCommerceChangeBaselineQueryPort):
    def __init__(self, rows: dict[str, tuple[float, float]]) -> None:
        self.rows = rows

    def find(self, year_quarter: str) -> SeoulCommerceChangeBaseline | None:
        pair = self.rows.get(year_quarter)
        return None if pair is None else SeoulCommerceChangeBaseline(year_quarter, *pair)


_BASELINE = FakeBaselinePort({"20262": (117.0, 52.0)})  # 20253은 baseline 없음


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
        lambda: RegionCommerceChangeQueryInteractor(port, _BASELINE)
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
    interactor = RegionCommerceChangeQueryInteractor(port, _BASELINE)

    with pytest.raises(MetricNotFoundError):
        interactor.list_metric_values("nonexistent", None)


def test_적재_전이면_빈_목록이다():
    interactor = RegionCommerceChangeQueryInteractor(FakeQueryPort([]), _BASELINE)

    assert interactor.list_metric_values("operating_months", None) == []


# --- 상세 계약 GET /commerce-changes/{region_code} (무대 설계서 §5-2) ---


def test_상세는_분기를_생략하면_그_동의_최신_분기를_주고_서울_평균을_동봉한다(client):
    body = client.get("/commerce-changes/1168064000").json()

    assert body["year_quarter"] == "20262"
    assert body["operating_months"] == 110.0 and body["closed_months"] == 48.0
    assert body["seoul"] == {"operating_months": 117.0, "closed_months": 52.0}


def test_baseline_행이_없는_분기면_seoul은_null이다(client):
    body = client.get("/commerce-changes/1168064000", params={"year_quarter": "20253"}).json()

    assert body["year_quarter"] == "20253" and body["operating_months"] == 104.0
    assert body["seoul"] is None


def test_없는_동은_404_COMMERCE_CHANGE_NOT_FOUND(client):
    response = client.get("/commerce-changes/9999999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMMERCE_CHANGE_NOT_FOUND"


def test_myself는_상세_경로에_행정동_코드로_잡히지_않는다(client):
    # `/{region_code}`를 목록·myself보다 뒤에 선언해야 한다
    assert client.get("/commerce-changes/myself").json()["region_code"] == "myself"
