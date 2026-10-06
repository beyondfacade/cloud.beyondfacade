"""verdict_facts_gateway — 판정 카드·대안을 LLM이 읽을 dict로 옮기는 경계 (DB 없음, 유스케이스 대역)."""

from datetime import datetime

from apps.agent.adapter.outbound.gateways import verdict_facts_gateway
from apps.agent.adapter.outbound.gateways.verdict_facts_gateway import VerdictFactsGateway
from apps.verdict.app.dtos.region_industry_verdict_dto import (
    AlternativeIndustryDto,
    AlternativeRegionDto,
    RegionIndustryVerdictDto,
    SignalResultDto,
    VerdictAlternativesDto,
)
from apps.verdict.domain.errors import IndustryNotFoundError

_VERDICT = RegionIndustryVerdictDto(
    region_code="1168064000",
    industry_id="cafe",
    verdict_code="red",
    strong_count=2,
    on_count=3,
    signals=(
        SignalResultDto(
            key="survival_cliff", level="strong", value=0.41, percentile=93.0,
            evidence="3년 생존율 41%로 서울 하위 7%입니다.", source="store",
        ),
        SignalResultDto(
            key="tobacco_gap", level="on", value=0.75, percentile=80.0,
            evidence="담배소매인 후보 자리 200곳 중 75%가 거리 제한에 막혀 있습니다.", source="tobacco",
        ),
    ),
    computed_at=datetime(2026, 9, 29, 3, 0, 0),
)

_ALTERNATIVES = VerdictAlternativesDto(
    region_code="1168064000",
    industry_id="cafe",
    neighborhood_type="office",
    industries=(
        AlternativeIndustryDto(
            industry_id="bakery", industry_name="제과점", verdict_code="clear",
            strong_count=0, on_count=0,
        ),
    ),
    regions=(
        AlternativeRegionDto(
            region_code="1168065000", region_name="역삼2동", verdict_code="orange",
            strong_count=0, on_count=1,
        ),
    ),
)


class FakeVerdictUseCase:
    """find/alternatives만 흉내 내는 대역 — 나머지 유스케이스 메서드는 게이트웨이가 쓰지 않는다."""

    def __init__(self, verdict=_VERDICT, alternatives=_ALTERNATIVES, error=None) -> None:
        self._verdict = verdict
        self._alternatives = alternatives
        self._error = error

    def find(self, region_code, industry_id):
        if self._error:
            raise self._error
        return self._verdict

    def alternatives(self, region_code, industry_id):
        if self._error:
            raise self._error
        return self._alternatives


def _gateway(monkeypatch, use_case) -> VerdictFactsGateway:
    monkeypatch.setattr(
        verdict_facts_gateway, "get_region_industry_verdict_use_case", lambda: use_case
    )
    return VerdictFactsGateway()


def test_판정을_카드_전_필드로_옮기고_산출일은_문자열로_준다(monkeypatch):
    payload = _gateway(monkeypatch, FakeVerdictUseCase()).verdict("1168064000", "cafe")

    assert payload["available"] is True
    assert payload["verdict_code"] == "red"
    assert (payload["strong_count"], payload["on_count"]) == (2, 3)
    assert payload["computed_at"] == "2026-09-29T03:00:00"
    assert payload["signals"][0]["percentile"] == 93.0
    assert payload["signals"][0]["evidence"].startswith("3년 생존율")


def test_참고_신호에는_advisory_표시가_붙는다(monkeypatch):
    """등급 계산에서 빠진 신호를 LLM이 켜진 경고로 쓰지 않게 값으로 구분해 준다 (설계서 §7)."""
    payload = _gateway(monkeypatch, FakeVerdictUseCase()).verdict("1168064000", "cafe")

    assert payload["signals"][0]["advisory"] is False
    assert payload["signals"][1]["advisory"] is True


def test_판정_대상_업종이_아니면_예외_대신_available_false를_준다(monkeypatch):
    gateway = _gateway(monkeypatch, FakeVerdictUseCase(error=IndustryNotFoundError("real_estate")))

    assert gateway.verdict("1168064000", "real_estate")["available"] is False
    assert gateway.alternatives("1168064000", "real_estate")["reason"]


def test_판정_행이_없으면_available_false와_이유를_준다(monkeypatch):
    gateway = _gateway(monkeypatch, FakeVerdictUseCase(verdict=None, alternatives=None))

    assert gateway.verdict("1168064000", "cafe")["available"] is False
    assert gateway.alternatives("1168064000", "cafe")["available"] is False


def test_대안_두_축을_그대로_옮긴다(monkeypatch):
    payload = _gateway(monkeypatch, FakeVerdictUseCase()).alternatives("1168064000", "cafe")

    assert payload["available"] is True
    assert payload["neighborhood_type"] == "office"
    assert payload["industries"][0]["industry_name"] == "제과점"
    assert payload["regions"][0]["region_name"] == "역삼2동"
