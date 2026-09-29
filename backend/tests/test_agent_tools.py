"""agent_tools — 도구 레지스트리 12종 + 월세vs매입 계산기 단위 테스트 (Fake 포트, DB 없음)."""

import json

from apps.agent.app.ports.output.agent_port import (
    FinanceFactsPort,
    FundingFactsPort,
    RegionFactsPort,
    VerdictFactsPort,
)
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

    def neighborhood_profile(self, region_code: str) -> dict:
        return {
            "region_code": region_code,
            "year_quarter": "20262",
            "type_code": "office",
            "type_name": "낮 인구 우위형",
            "type_reason": "직장인구가 상주인구의 5.9배로 서울 상위 10%입니다.",
            "time_label": "낮(11~17시)",
            "peak_block": "낮(11~17시)",
            "trough_block": "밤(21~06시)",
            "footfall_age_mix": [{"age": "30", "share": 0.24}, {"age": "20", "share": 0.22}],
            "worker_resident_ratio": 5.93,
            "weekend_index": 0.7,
            "night_index": 0.64,
            "fnb_share": 0.016,
            "facility_total": 542,
            "resident_total": 34082,
            "commerce_change": {"code": "LL", "name": "다이나믹", "operating_months": 110.0},
            "top_facilities": [{"type": "버스정거장", "count": 120}],
            "apartment_avg_price_won": 307439893,
            "benchmarks": {
                "seoul": {"operating_months": 118.0, "closed_months": 54.0},
                "type_median": {
                    "weekend_index": 0.81,
                    "night_index": 0.695,
                    "fnb_share": 0.161,
                    "worker_resident_ratio": 2.714,
                },
                "type_count": 36,
            },
            "caveats": ["아파트 평균 시가는 참고값이다."],
        }


class FakeRagSearchUseCase(RagSearchUseCase):
    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        return []


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


class FakeFundingFactsPort(FundingFactsPort):
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def candidates(self, industry_id, external_funding_need, stage) -> dict:
        self.calls.append((industry_id, external_funding_need, stage))
        return {
            "candidates": [
                {
                    "title": "2026년 소상공인 정책자금 융자사업",
                    "org": "중소벤처기업부",
                    "url": "https://example.test/1",
                    "apply_period": "상시",
                    "deadline": None,
                    "field_category": "금융",
                    "summary": "운전자금·시설자금 융자",
                    "why": "전국 · 소상공인 · 금융",
                }
            ],
            "industry_id": industry_id,
            "external_funding_need": external_funding_need,
            "stage": stage,
            "disclaimer": "자격 확정이 아니라 해당 가능성이 있는 공고다",
        }


class FakeVerdictFactsPort(VerdictFactsPort):
    """판정 카드·대안 Fake — 게이트웨이가 만들어 주는 dict 형태를 그대로 흉내 낸다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def verdict(self, region_code: str, industry_id: str) -> dict:
        self.calls.append(("verdict", region_code, industry_id))
        return {
            "available": True,
            "region_code": region_code,
            "industry_id": industry_id,
            "verdict_code": "red",
            "strong_count": 2,
            "on_count": 3,
            "signals": [
                {
                    "key": "survival_cliff",
                    "level": "strong",
                    "value": 0.41,
                    "percentile": 93.0,
                    "evidence": "3년 생존율 41%로 서울 하위 7%입니다.",
                    "source": "store",
                    "advisory": False,
                },
                {
                    "key": "shrinking",
                    "level": "on",
                    "value": None,
                    "percentile": None,
                    "evidence": "서울시 상권변화지표가 '상권축소'입니다.",
                    "source": "neighborhood",
                    "advisory": True,
                },
            ],
            "computed_at": "2026-09-29T00:00:00",
        }

    def alternatives(self, region_code: str, industry_id: str) -> dict:
        self.calls.append(("alternatives", region_code, industry_id))
        return {
            "available": True,
            "region_code": region_code,
            "industry_id": industry_id,
            "neighborhood_type": "office",
            "industries": [
                {
                    "industry_id": "bakery",
                    "industry_name": "제과점",
                    "verdict_code": "clear",
                    "strong_count": 0,
                    "on_count": 0,
                }
            ],
            "regions": [],
        }


class UnavailableVerdictFactsPort(FakeVerdictFactsPort):
    """판정 없음·대상 아님 — 게이트웨이가 예외를 삼키고 돌려주는 형태."""

    def verdict(self, region_code: str, industry_id: str) -> dict:
        return {"available": False, "reason": "판정 대상 업종이 아닙니다"}

    def alternatives(self, region_code: str, industry_id: str) -> dict:
        return {"available": False, "reason": "판정 대상 업종이 아닙니다"}


def _build_tools(
    finance: FinanceFactsPort | None = None,
    funding: FundingFactsPort | None = None,
    verdict: VerdictFactsPort | None = None,
    budget: int | None = None,
) -> list:
    return build_tools(
        FakeRegionFactsPort(),
        FakeRagSearchUseCase(),
        finance or FakeFinanceFactsPort(),
        funding or FakeFundingFactsPort(),
        verdict or FakeVerdictFactsPort(),
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


def test_build_tools_returns_9_tools_with_correct_name_and_stage():
    """12종 도구 name/stage 정확 매핑."""
    tools = _build_tools()

    by_name = {tool.spec.name: tool.stage for tool in tools}

    assert by_name == {
        "get_verdict": "verdict",
        "get_verdict_alternatives": "verdict",
        "get_region_metrics": "market",
        "get_region_summary": "market",
        "get_neighborhood_profile": "market",
        "get_population": "market",
        "search_shocks": "shock",
        "search_news": "shock",
        "search_funding": "funding",
        "get_funding_candidates": "funding",
        "run_finance_simulation": "funding",
        "compare_rent_vs_buy": "funding",
    }


# 인자 없이 불러도 뜻이 서는 도구 — 라우터도 세 파라미터를 전부 선택으로 받는다.
# 억지 required를 세우면 스키마가 거짓말이 되고 LLM이 값을 지어내게 된다.
_TOOLS_WITHOUT_REQUIRED = {"get_funding_candidates"}


def test_every_tool_input_schema_declares_required_params():
    """인자가 뜻을 가르는 도구는 required를 선언한다 — 예외는 명시한 것뿐."""
    tools = _build_tools()

    for tool in tools:
        if tool.spec.name in _TOOLS_WITHOUT_REQUIRED:
            assert tool.spec.input_schema["required"] == []
            continue
        required = tool.spec.input_schema.get("required")
        assert required, f"{tool.spec.name}에 required 파라미터가 없다"


def test_get_region_metrics_run_returns_json_string_via_fake_port():
    """get_region_metrics.run은 RegionFactsPort.metrics 결과를 압축 JSON 문자열로 반환한다."""
    facts = FakeRegionFactsPort()
    tools = build_tools(
        facts,
        FakeRagSearchUseCase(),
        FakeFinanceFactsPort(),
        FakeFundingFactsPort(),
        FakeVerdictFactsPort(),
    )
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

    tools = build_tools(
        RatelessRegionFactsPort(),
        FakeRagSearchUseCase(),
        FakeFinanceFactsPort(),
        FakeFundingFactsPort(),
        FakeVerdictFactsPort(),
    )
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


def test_get_neighborhood_profile_run_returns_market_slot_material():
    """market 여섯 슬롯이 각각 기댈 키가 도구 결과에 있다 (설계서 §7-4 출력 계약)."""
    tools = _build_tools()
    tool = next(t for t in tools if t.spec.name == "get_neighborhood_profile")

    payload = json.loads(tool.run({"region_code": "1168064000"}))

    assert payload["type_name"] == "낮 인구 우위형"  # 한 줄 요약
    assert payload["type_reason"]  # 동네 설명
    assert payload["footfall_age_mix"][0]["age"] == "30"  # 고객 구성
    assert (payload["peak_block"], payload["trough_block"]) == (
        "낮(11~17시)",
        "밤(21~06시)",
    )  # 시간대 특성
    assert payload["weekend_index"] is not None and payload["night_index"] is not None  # 주의점
    assert payload["commerce_change"]["name"] == "다이나믹"  # 확인할 것
    assert payload["apartment_avg_price_won"] == 307439893


def test_get_neighborhood_profile_carries_caveats_so_llm_does_not_misread():
    """해석 금지 사항을 수치와 함께 넘긴다 — 결측을 0으로 읽는 실수를 막는다."""
    tools = _build_tools()
    tool = next(t for t in tools if t.spec.name == "get_neighborhood_profile")

    payload = json.loads(tool.run({"region_code": "1168064000"}))

    assert payload["caveats"]


def test_get_neighborhood_profile_cites_the_derived_table():
    tools = _build_tools()
    tool = next(t for t in tools if t.spec.name == "get_neighborhood_profile")

    citations = tool.cite({"region_code": "1168064000"}, "{}")

    assert citations == [
        {
            "grade": "fact",
            "source": "region_profile_quarter",
            "region_code": "1168064000",
        }
    ]


def test_get_neighborhood_profile_carries_benchmarks_for_comparison():
    """market 절이 패널의 반복이 아니라 다음 층이 되려면 비교 기준이 도구 결과에 있어야 한다 (무대 설계서 §7)."""
    tools = _build_tools()
    tool = next(t for t in tools if t.spec.name == "get_neighborhood_profile")

    payload = json.loads(tool.run({"region_code": "1168064000"}))

    benchmarks = payload["benchmarks"]
    assert benchmarks["seoul"] == {"operating_months": 118.0, "closed_months": 54.0}
    assert set(benchmarks["type_median"]) == {
        "weekend_index", "night_index", "fnb_share", "worker_resident_ratio"
    }
    assert benchmarks["type_count"] == 36


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
    assert tool.stage == "funding"  # SSE agent_status 어휘는 verdict|market|shock|funding — 계산기 스테이지는 없다
    assert tool.cite({}, "{}") == [{"grade": "fact", "source": "finance_engine"}]


def test_compare_rent_vs_buy_is_kept_alongside_the_engine_tool():
    names = {t.spec.name for t in _build_tools()}

    assert {"compare_rent_vs_buy", "run_finance_simulation"} <= names


def test_get_funding_candidates_returns_filtered_programs_with_disclaimer():
    """결정론 필터 결과 — 자격 확정이 아님을 LLM이 매번 보게 함께 싣는다 (설계서 §6)."""
    funding = FakeFundingFactsPort()
    tool = next(t for t in _build_tools(funding=funding) if t.spec.name == "get_funding_candidates")

    payload = json.loads(tool.run({"industry_id": "cafe", "external_funding_need": 31_600_000, "stage": "pre"}))

    assert funding.calls == [("cafe", 31_600_000, "pre")]
    assert payload["candidates"][0]["why"] == "전국 · 소상공인 · 금융"
    assert "자격 확정이 아니" in payload["disclaimer"]
    assert payload["external_funding_need"] == 31_600_000


def test_get_funding_candidates_accepts_no_arguments():
    """세 인자 모두 선택 — 지역·대상만으로도 후보를 낸다."""
    tool = next(t for t in _build_tools() if t.spec.name == "get_funding_candidates")

    assert tool.spec.input_schema["required"] == []
    assert json.loads(tool.run({}))["candidates"]


def test_get_funding_candidates_cites_each_program_url():
    """후보는 RAG 신호가 아니라 결정론 필터 결과라 fact 등급이고, 원문 링크가 근거다."""
    tool = next(t for t in _build_tools() if t.spec.name == "get_funding_candidates")
    result = tool.run({})

    citations = tool.cite({}, result)

    assert citations == [
        {
            "grade": "fact",
            "source": "funding_program",
            "title": "2026년 소상공인 정책자금 융자사업",
            "url": "https://example.test/1",
        }
    ]


# --- verdict 스테이지 도구 2종 (설계서 §5-2) ---


def test_판정_도구가_다른_스테이지보다_먼저_배치된다():
    """리포트 첫 섹션이 판정이라 LLM이 판정부터 읽게 한다 — 목록 앞자리가 그 신호다."""
    tools = _build_tools()

    assert [t.spec.name for t in tools[:2]] == ["get_verdict", "get_verdict_alternatives"]
    assert [t.stage for t in tools[:2]] == ["verdict", "verdict"]


def test_get_verdict가_카드_전_필드를_참고_신호_표시와_함께_돌려준다():
    """등급·신호·근거·백분위·산출일을 그대로 옮기고, 참고 신호는 advisory로 구분한다."""
    verdict = FakeVerdictFactsPort()
    tool = next(t for t in _build_tools(verdict=verdict) if t.spec.name == "get_verdict")

    payload = json.loads(tool.run({"region_code": "1168064000", "industry_id": "cafe"}))

    assert verdict.calls == [("verdict", "1168064000", "cafe")]
    assert payload["verdict_code"] == "red"
    assert (payload["strong_count"], payload["on_count"]) == (2, 3)
    assert payload["computed_at"] == "2026-09-29T00:00:00"
    assert payload["signals"][0]["evidence"].startswith("3년 생존율")
    assert payload["signals"][0]["advisory"] is False
    assert payload["signals"][1]["advisory"] is True  # 상권 축소는 경고가 아니라 참고


def test_get_verdict_alternatives가_두_축을_그대로_돌려준다():
    verdict = FakeVerdictFactsPort()
    tool = next(
        t for t in _build_tools(verdict=verdict) if t.spec.name == "get_verdict_alternatives"
    )

    payload = json.loads(tool.run({"region_code": "1168064000", "industry_id": "cafe"}))

    assert verdict.calls == [("alternatives", "1168064000", "cafe")]
    assert payload["industries"][0]["industry_name"] == "제과점"
    assert payload["regions"] == []


def test_판정이_없으면_도구가_available_false와_이유를_돌려준다():
    """예외가 아니라 값으로 돌려줘야 LLM이 '판정 없음'을 그대로 쓸 수 있다."""
    tools = _build_tools(verdict=UnavailableVerdictFactsPort())

    for name in ("get_verdict", "get_verdict_alternatives"):
        tool = next(t for t in tools if t.spec.name == name)
        payload = json.loads(tool.run({"region_code": "1168064000", "industry_id": "real_estate"}))
        assert payload == {"available": False, "reason": "판정 대상 업종이 아닙니다"}


def test_판정_도구는_판정_테이블을_인용한다():
    tool = next(t for t in _build_tools() if t.spec.name == "get_verdict")

    citations = tool.cite({"region_code": "1168064000", "industry_id": "cafe"}, "{}")

    assert citations == [
        {
            "grade": "fact",
            "source": "region_industry_verdict",
            "region_code": "1168064000",
            "industry_id": "cafe",
        }
    ]


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
