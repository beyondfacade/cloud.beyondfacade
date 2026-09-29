"""verdict 라우터 — 배선(myself) · 목록(범주 계약) · 단건 · 404 두 종류 (Fake 유스케이스)."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    AlternativeIndustryDto,
    AlternativeRegionDto,
    RegionIndustryVerdictDto,
    SignalResultDto,
    VerdictAlternativesDto,
    VerdictValueDto,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.errors import IndustryNotFoundError
from main import app

_DTO = RegionIndustryVerdictDto(
    region_code="1168064000", industry_id="korean_food", verdict_code="red", strong_count=2, on_count=3,
    signals=tuple(
        SignalResultDto(key=k, level="strong", value=0.2, percentile=95.0, evidence="근거", source="store")
        for k in ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    ),
    computed_at=datetime(2026, 9, 29, 4, 30, tzinfo=timezone.utc),
)


class FakeUseCase(RegionIndustryVerdictUseCase):
    def myself(self):
        return _DTO

    def build(self, today):
        return 0

    def list_verdict_values(self, industry_id):
        if industry_id != "korean_food":
            raise IndustryNotFoundError(industry_id)
        return [VerdictValueDto("1168064000", "red"), VerdictValueDto("1168065000", "clear")]

    def find(self, region_code, industry_id):
        if industry_id != "korean_food":
            raise IndustryNotFoundError(industry_id)
        return _DTO if region_code == "1168064000" else None

    def alternatives(self, region_code, industry_id):
        if industry_id != "korean_food":
            raise IndustryNotFoundError(industry_id)
        if region_code != "1168064000":
            return None
        return VerdictAlternativesDto(
            region_code=region_code, industry_id=industry_id, neighborhood_type="office",
            industries=(AlternativeIndustryDto("snack", "분식", "clear", 0, 0),),
            regions=(AlternativeRegionDto("1168065000", "삼성1동", "orange", 0, 1),),
        )


def _client() -> TestClient:
    app.dependency_overrides[get_region_industry_verdict_use_case] = lambda: FakeUseCase()
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_region_industry_verdict_use_case, None)


def test_myself_배선_200():
    app.dependency_overrides.pop(get_region_industry_verdict_use_case, None)  # 실제 DI로 배선 검증
    body = TestClient(app).get("/verdicts/myself").json()
    assert body["region_code"] == "myself" and len(body["signals"]) == 5


def test_목록은_region_code와_value_쌍이다():
    res = _client().get("/verdicts?industry=korean_food")
    assert res.status_code == 200
    assert res.json() == [{"region_code": "1168064000", "value": "red"}, {"region_code": "1168065000", "value": "clear"}]


def test_판정_대상이_아닌_업종은_404_INDUSTRY_NOT_FOUND():
    res = _client().get("/verdicts?industry=academy")
    assert res.status_code == 404 and res.json()["error"]["code"] == "INDUSTRY_NOT_FOUND"
    res = _client().get("/verdicts/1168064000?industry=chicken")
    assert res.status_code == 404 and res.json()["error"]["code"] == "INDUSTRY_NOT_FOUND"


def test_단건은_신호_5개를_담고_없으면_404_VERDICT_NOT_FOUND():
    res = _client().get("/verdicts/1168064000?industry=korean_food")
    assert res.status_code == 200
    body = res.json()
    assert body["verdict_code"] == "red" and body["signals"][0]["key"] == "net_outflow"
    assert body["signals"][0]["percentile"] == 95.0
    missing = _client().get("/verdicts/0000000000?industry=korean_food")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "VERDICT_NOT_FOUND"


def test_대안은_두_축을_담고_404는_단건과_같다():
    res = _client().get("/verdicts/1168064000/alternatives?industry=korean_food")
    assert res.status_code == 200
    body = res.json()
    assert body["neighborhood_type"] == "office"
    assert body["industries"] == [{"industry_id": "snack", "industry_name": "분식", "verdict_code": "clear", "strong_count": 0, "on_count": 0}]
    assert body["regions"][0]["region_name"] == "삼성1동"
    assert _client().get("/verdicts/1168064000/alternatives?industry=chicken").json()["error"]["code"] == "INDUSTRY_NOT_FOUND"
    missing = _client().get("/verdicts/0000000000/alternatives?industry=korean_food")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "VERDICT_NOT_FOUND"
