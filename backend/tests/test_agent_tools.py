"""agent_tools — facts가 대신할 수 없는 도구 4종 + 월세vs매입 계산기 (Fake 포트, DB 없음)."""

import json

from apps.agent.app.ports.output.agent_port import FinanceFactsPort, RegionFactsPort
from apps.agent.app.use_cases.agent_tools import build_tools, compare_rent_vs_buy
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit


class FakeRegionFactsPort(RegionFactsPort):
    """도구가 쓰는 것은 최신 금리뿐이다 — 나머지 사실은 facts 선수집이 가져간다."""

    def metrics_history(self, region_code: str, industry_id: str) -> list[dict]:
        return []

    def summary(self, region_code: str, industry_id: str) -> dict:
        return {}

    def population(self, region_code: str) -> dict:
        return {}

    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        return []

    def latest_rates(self) -> dict:
        return {"loan_facility": 4.5}

    def neighborhood_profile(self, region_code: str) -> dict:
        return {}

    def hour_gap(self, region_code: str, industry_id: str) -> dict:
        return {}

    def commerce_change_detail(self, region_code: str) -> dict:
        return {}


class FakeRagSearchUseCase(RagSearchUseCase):
    """질의·source_type을 기록하고 결과 1건을 돌려준다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str | None]] = []

    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        self.calls.append((query, top_k, source_type))
        return [
            RagHit(
                chunk_id=f"{source_type}:1",
                source_type=source_type or "news",
                source_id="1",
                content="본문",
                score=0.7,
                url="https://example.test/1",
                org="한국일보",
                published_at=None,
            )
        ]


class FakeFinanceFactsPort(FinanceFactsPort):
    """엔진을 흉내 내지 않는다 — 받은 입력을 기록하고 고정 결과를 돌려준다."""

    def __init__(self) -> None:
        self.inputs: list[dict] = []

    def simulate(self, input: dict) -> dict:
        self.inputs.append(input)
        return {
            "capex": 50_000_000,
            "monthly_fixed": 3_500_000,
            "bep_revenue": 9_000_000,
            "funding_gap": 6_600_000,
            "reserve_months": 6,
            "operating_reserve": 21_600_000,
            "total_required_funds": 71_600_000,
            "external_funding_need": 31_600_000,
            "scenarios": [],
            "stress": [],
            "assumptions": "공시 평균 금리 기반 예상치",
        }


def _build_tools(
    finance: FinanceFactsPort | None = None,
    rag: RagSearchUseCase | None = None,
    region: RegionFactsPort | None = None,
    budget: int | None = None,
) -> list:
    return build_tools(
        region or FakeRegionFactsPort(),
        rag or FakeRagSearchUseCase(),
        finance or FakeFinanceFactsPort(),
        budget,
    )


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


def test_facts가_대신할_수_없는_네_도구만_남는다():
    """판정·지표·프로필·인구·충격·공고 후보는 facts 선수집이 이미 가져온다 (설계서 §3-3②)."""
    by_name = {tool.spec.name: tool.stage for tool in _build_tools()}

    assert by_name == {
        "search_news": "shock",
        "search_funding": "funding",
        "run_finance_simulation": "funding",
        "compare_rent_vs_buy": "funding",
    }


def test_every_tool_input_schema_declares_required_params():
    """인자가 뜻을 가르는 도구는 required를 선언한다 — 남은 4종은 모두 인자가 필수다."""
    for tool in _build_tools():
        assert tool.spec.input_schema.get("required"), f"{tool.spec.name}에 required 파라미터가 없다"


def test_검색_도구는_source_type을_나눠_묻는다():
    """뉴스와 공고는 같은 색인의 다른 원천이다 — 섞이면 [참고 신호] 표기가 무너진다."""
    rag = FakeRagSearchUseCase()
    tools = _build_tools(rag=rag)

    for name, source_type in (("search_news", "news"), ("search_funding", "funding")):
        tool = next(t for t in tools if t.spec.name == name)
        payload = json.loads(tool.run({"query": "역삼1동 한식"}))
        assert payload[0]["org"] == "한국일보"

    assert rag.calls == [("역삼1동 한식", 5, "news"), ("역삼1동 한식", 5, "funding")]


def test_검색_도구는_RAG_결과를_참고_신호로_인용한다():
    tool = next(t for t in _build_tools() if t.spec.name == "search_news")
    result = tool.run({"query": "역삼1동 한식"})

    citations = tool.cite({}, result)

    assert citations == [
        {
            "grade": "signal",
            "source_type": "news",
            "source_id": "1",
            "url": "https://example.test/1",
            "org": "한국일보",
        }
    ]


def test_compare_rent_vs_buy_tool_returns_error_payload_when_loan_facility_rate_missing():
    """annual_rate_pct 생략 + latest_rates()에 loan_facility 부재 → 오류 JSON(예외 아님)."""

    class RatelessRegionFactsPort(FakeRegionFactsPort):
        def latest_rates(self) -> dict:
            return {}

    tools = _build_tools(region=RatelessRegionFactsPort())
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


_ENGINE_INPUT = {
    "deposit": 20_000_000, "key_money": 0, "interior_cost": 20_000_000, "equipment_cost": 10_000_000,
    "monthly_rent": 2_500_000, "monthly_payroll": 900_000, "monthly_insurance": 100_000,
    "cost_ratio": 0.57, "fee_ratio": 0.03, "equity": 40_000_000, "desired_loan": 25_000_000,
    "loan_rate": 0.048, "expected_monthly_revenue": 8_000_000,
}


def test_run_finance_simulation_passes_13_fields_and_returns_headline_keys():
    """계산은 finance BC가 한다 — 도구는 입력을 그대로 넘기고 결과 표를 JSON으로 돌려준다."""
    finance = FakeFinanceFactsPort()
    tool = next(t for t in _build_tools(finance) if t.spec.name == "run_finance_simulation")

    payload = json.loads(tool.run(dict(_ENGINE_INPUT)))

    assert finance.inputs == [_ENGINE_INPUT]
    assert payload["external_funding_need"] == 31_600_000  # 헤드라인
    assert payload["funding_gap"] == 6_600_000  # 보조 — 0이어도 "충분"이 아니다
    assert {"total_required_funds", "bep_revenue", "monthly_fixed", "capex", "scenarios", "stress"} <= set(payload)
    assert "예상치" in payload["assumptions"]


def test_run_finance_simulation_requires_all_13_fields_and_cites_the_engine():
    tool = next(t for t in _build_tools() if t.spec.name == "run_finance_simulation")

    assert set(tool.spec.input_schema["required"]) == set(_ENGINE_INPUT)
    assert tool.stage == "funding"  # SSE agent_status 어휘에 계산기 스테이지는 없다
    assert tool.cite({}, "{}") == [{"grade": "fact", "source": "finance_engine"}]


# --- 세션 예산 → finance 도구 기본값 (설계서 §5-2) ---


def test_예산을_주면_자기자본을_생략해도_예산이_기본값으로_들어간다():
    finance = FakeFinanceFactsPort()
    tool = next(
        t
        for t in _build_tools(finance=finance, budget=50_000_000)
        if t.spec.name == "run_finance_simulation"
    )
    without_equity = {k: v for k, v in _ENGINE_INPUT.items() if k != "equity"}

    tool.run(dict(without_equity))

    assert finance.inputs == [{**without_equity, "equity": 50_000_000}]
    assert "equity" not in tool.spec.input_schema["required"]  # 생략이 가능해야 기본값이 뜻을 갖는다


def test_예산이_있어도_LLM이_준_자기자본이_이긴다():
    finance = FakeFinanceFactsPort()
    tool = next(
        t
        for t in _build_tools(finance=finance, budget=50_000_000)
        if t.spec.name == "run_finance_simulation"
    )

    tool.run(dict(_ENGINE_INPUT))

    assert finance.inputs == [_ENGINE_INPUT]


def test_예산이_없으면_자기자본은_그대로_필수다():
    """기존 요청(budget 없음)의 스키마는 한 글자도 달라지지 않는다."""
    tool = next(t for t in _build_tools() if t.spec.name == "run_finance_simulation")

    assert "equity" in tool.spec.input_schema["required"]
