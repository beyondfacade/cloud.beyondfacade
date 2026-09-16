"""agent_tools — 도구 레지스트리 7종 + 월세vs매입 계산기 단위 테스트 (Fake 포트, DB 없음)."""

import json

from apps.agent.app.ports.output.agent_port import RegionFactsPort
from apps.agent.app.use_cases.agent_tools import build_tools, compare_rent_vs_buy
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit


class FakeRegionFactsPort(RegionFactsPort):
    """호출 인자 기록용 Fake — DB 없이 고정 데이터 반환."""

    def __init__(self) -> None:
        self.metrics_calls: list[tuple[str, str]] = []

    def metrics(self, region_code: str, industry: str) -> list[dict]:
        self.metrics_calls.append((region_code, industry))
        return [
            {
                "year": 2026,
                "store_count": 10,
                "closure_rate": 0.1,
                "growth_rate": 0.05,
            }
        ]

    def summary(self, region_code: str, industry_id: str) -> dict:
        return {"region_code": region_code, "industry_id": industry_id, "cards": []}

    def population(self, region_code: str) -> dict:
        return {
            "region_code": region_code,
            "period": "202601",
            "age_distribution": {},
            "school_age_population": 0,
        }

    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        return []

    def latest_rates(self) -> dict:
        return {"loan_facility": 4.5}


class FakeRagSearchUseCase(RagSearchUseCase):
    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        return []


def _build_tools() -> list:
    return build_tools(FakeRegionFactsPort(), FakeRagSearchUseCase())


def test_compare_rent_vs_buy_calculates_expected_values():
    """정상 케이스 — 대출액·월이자·월절감·취득부대·손익분기년 산식 검증."""
    result = compare_rent_vs_buy(
        monthly_rent_manwon=200,
        purchase_price_manwon=30000,
        equity_manwon=10000,
        annual_rate_pct=4.5,
    )

    assert result["loan_manwon"] == 20000
    assert result["monthly_interest_manwon"] == 75
    assert result["monthly_saving_manwon"] == 125
    assert result["acquisition_cost_manwon"] == 1380
    assert result["breakeven_years"] == 1380 / 1500
    assert result["assumptions"] == "공시 평균 금리 기반 예상치, 실제 심사와 다를 수 있음"


def test_compare_rent_vs_buy_equity_exceeds_price_gives_zero_loan():
    """자기자본이 매입가를 넘으면 대출액은 0(음수 방지)."""
    result = compare_rent_vs_buy(
        monthly_rent_manwon=100,
        purchase_price_manwon=10000,
        equity_manwon=15000,
        annual_rate_pct=4.0,
    )

    assert result["loan_manwon"] == 0
    assert result["monthly_interest_manwon"] == 0


def test_compare_rent_vs_buy_monthly_interest_exceeds_rent_gives_none_breakeven():
    """월이자가 월세 이상이면 손익분기년은 None."""
    result = compare_rent_vs_buy(
        monthly_rent_manwon=50,
        purchase_price_manwon=30000,
        equity_manwon=0,
        annual_rate_pct=12,
    )

    assert result["monthly_saving_manwon"] <= 0
    assert result["breakeven_years"] is None


def test_build_tools_returns_7_tools_with_correct_name_and_stage():
    """7종 도구 name/stage 정확 매핑."""
    tools = _build_tools()

    by_name = {tool.spec.name: tool.stage for tool in tools}

    assert by_name == {
        "get_region_metrics": "market",
        "get_region_summary": "market",
        "get_population": "market",
        "search_shocks": "shock",
        "search_news": "shock",
        "search_funding": "funding",
        "compare_rent_vs_buy": "funding",
    }


def test_every_tool_input_schema_declares_required_params():
    """모든 도구 spec.input_schema에 required 파라미터가 존재한다."""
    tools = _build_tools()

    for tool in tools:
        required = tool.spec.input_schema.get("required")
        assert required, f"{tool.spec.name}에 required 파라미터가 없다"


def test_get_region_metrics_run_returns_json_string_via_fake_port():
    """get_region_metrics.run은 RegionFactsPort.metrics 결과를 압축 JSON 문자열로 반환한다."""
    facts = FakeRegionFactsPort()
    tools = build_tools(facts, FakeRagSearchUseCase())
    tool = next(t for t in tools if t.spec.name == "get_region_metrics")

    result = tool.run({"region_code": "11010", "industry": "cafe"})

    assert isinstance(result, str)
    assert json.loads(result) == [
        {"year": 2026, "store_count": 10, "closure_rate": 0.1, "growth_rate": 0.05}
    ]
    assert facts.metrics_calls == [("11010", "cafe")]


def test_compare_rent_vs_buy_tool_returns_error_payload_when_loan_facility_rate_missing():
    """annual_rate_pct 생략 + latest_rates()에 loan_facility 부재 → 오류 JSON(예외 아님)."""

    class RatelessRegionFactsPort(FakeRegionFactsPort):
        def latest_rates(self) -> dict:
            return {}

    tools = build_tools(RatelessRegionFactsPort(), FakeRagSearchUseCase())
    tool = next(t for t in tools if t.spec.name == "compare_rent_vs_buy")

    result = tool.run(
        {
            "monthly_rent_manwon": 200,
            "purchase_price_manwon": 30000,
            "equity_manwon": 10000,
        }
    )

    assert json.loads(result) == {
        "error": "시설자금대출 금리 데이터가 없어 연금리를 지정해야 합니다"
    }
