"""region summary 검증 — 카드 3장 포맷·데이터 없음·404 에러 바디 (Fake 포트).

프론트엔드 계약: {region_code, name, industry_id, cards:[{label, value, grade}]},
grade는 fact(집계 수치) — 최신 연도(2026) region_industry_metric 기준.
"""

import pytest
from fastapi.testclient import TestClient

from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.app.ports.output.region_port import (
    RegionBoundaryReaderPort,
    RegionMetricSummaryPort,
    RegionRepositoryPort,
)
from apps.master.app.use_cases.region_interactor import RegionInteractor
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.master.domain.entities.region_entity import Region
from apps.master.domain.errors import RegionNotFoundError
from main import app

_YEOKSAM1 = Region(region_code="1168064000", district_code="11680", name="역삼1동")


class FakeRepository(RegionRepositoryPort):
    def __init__(self, regions: list[Region]) -> None:
        self._regions = regions

    def list_regions(self) -> list[Region]:
        return self._regions

    def find(self, region_code: str) -> Region | None:
        return next((r for r in self._regions if r.region_code == region_code), None)


class FakeBoundaryReader(RegionBoundaryReaderPort):
    def read_feature(self, geometry_ref: str) -> dict:
        raise NotImplementedError


class FakeMetricSummary(RegionMetricSummaryPort):
    def __init__(self, snapshot: RegionMetricSnapshot | None) -> None:
        self._snapshot = snapshot

    def fetch(self, region_code: str, industry_id: str) -> RegionMetricSnapshot | None:
        return self._snapshot


def _interactor(snapshot: RegionMetricSnapshot | None) -> RegionInteractor:
    return RegionInteractor(
        repository=FakeRepository([_YEOKSAM1]),
        boundary_reader=FakeBoundaryReader(),
        metric_summary=FakeMetricSummary(snapshot),
    )


def test_summary_formats_three_fact_cards():
    snapshot = RegionMetricSnapshot(store_count=705, closure_rate=0.0527, growth_rate=0.0322)
    dto = _interactor(snapshot).summary("1168064000", "cafe")

    assert dto.region_code == "1168064000"
    assert dto.name == "역삼1동"
    assert dto.industry_id == "cafe"
    assert [(c.label, c.value, c.grade) for c in dto.cards] == [
        ("점포수", "705개", "fact"),
        ("폐업률", "5.3%", "fact"),
        ("성장률", "+3.2%", "fact"),
    ]


def test_summary_signs_negative_growth_rate():
    snapshot = RegionMetricSnapshot(store_count=10, closure_rate=0.1491, growth_rate=-0.0246)
    dto = _interactor(snapshot).summary("1168064000", "cafe")
    assert dto.cards[2].value == "-2.5%"


def test_summary_uses_no_data_when_metric_missing():
    dto = _interactor(None).summary("1168064000", "cafe")
    assert [(c.label, c.value) for c in dto.cards] == [
        ("점포수", "데이터 없음"),
        ("폐업률", "데이터 없음"),
        ("성장률", "데이터 없음"),
    ]


def test_summary_uses_no_data_for_none_rates():
    snapshot = RegionMetricSnapshot(store_count=5, closure_rate=None, growth_rate=None)
    dto = _interactor(snapshot).summary("1168064000", "cafe")
    assert [c.value for c in dto.cards] == ["5개", "데이터 없음", "데이터 없음"]


def test_summary_rejects_unknown_region():
    with pytest.raises(RegionNotFoundError):
        _interactor(None).summary("9999999999", "cafe")


def _client(snapshot: RegionMetricSnapshot | None) -> TestClient:
    fake: RegionUseCase = _interactor(snapshot)
    app.dependency_overrides[get_region_use_case] = lambda: fake
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_summary_endpoint_returns_contract_shape():
    client = _client(RegionMetricSnapshot(store_count=705, closure_rate=0.0527, growth_rate=0.0322))
    response = client.get("/regions/1168064000/summary?industry=cafe")
    assert response.status_code == 200
    body = response.json()
    assert body["region_code"] == "1168064000"
    assert body["cards"][0] == {"label": "점포수", "value": "705개", "grade": "fact"}


def test_summary_endpoint_404_on_unknown_region():
    client = _client(None)
    response = client.get("/regions/9999999999/summary?industry=cafe")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "REGION_NOT_FOUND"
    assert body["error"]["message"]
