"""Application UseCase — LLM 도구 레지스트리(테이블, GoF Strategy) + 월세vs매입 계산기.

`app/` 레이어는 어댑터·ORM·타 BC 의존성을 직접 import하지 않는다.
cross-BC 조회는 RegionFactsPort(agent_port.py) 뒤로 숨긴다.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from apps.agent.app.ports.output.agent_port import (
    FinanceFactsPort,
    FundingFactsPort,
    LLMToolSpec,
    RegionFactsPort,
)
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit

_ACQUISITION_COST_RATE = 0.046  # 매입 부대비용(취득세 등) 개산율 — §8.1③


@dataclass
class AgentTool:
    """LLM에 노출할 도구 1개 — spec(스키마) + stage(SSE 매핑) + run(실행) + cite(인용 추출)."""

    spec: LLMToolSpec
    stage: str  # "market" | "shock" | "funding" — SSE agent_status 매핑
    run: Callable[[dict], str]  # 결과는 LLM에 넣을 압축 JSON 문자열
    cite: Callable[[dict, str], list[dict]] | None = None  # (args, result) -> citations 항목


def compare_rent_vs_buy(
    monthly_rent_manwon: float,
    purchase_price_manwon: float,
    equity_manwon: float,
    annual_rate_pct: float,
) -> dict:
    """월세 vs 매입 비교 (§8.1③).

    대출액=매입가−자기자본(음수면 0), 월이자=대출액×연금리/100/12,
    월절감=월세−월이자, 취득부대=매입가×0.046,
    손익분기년=월절감>0일 때 취득부대/(월절감×12), 아니면 None.
    """
    loan_manwon = max(purchase_price_manwon - equity_manwon, 0)
    monthly_interest_manwon = loan_manwon * annual_rate_pct / 100 / 12
    monthly_saving_manwon = monthly_rent_manwon - monthly_interest_manwon
    acquisition_cost_manwon = purchase_price_manwon * _ACQUISITION_COST_RATE
    breakeven_years = (
        acquisition_cost_manwon / (monthly_saving_manwon * 12)
        if monthly_saving_manwon > 0
        else None
    )
    return {
        "loan_manwon": loan_manwon,
        "monthly_interest_manwon": monthly_interest_manwon,
        "monthly_saving_manwon": monthly_saving_manwon,
        "acquisition_cost_manwon": acquisition_cost_manwon,
        "breakeven_years": breakeven_years,
        "assumptions": "공시 평균 금리 기반 예상치, 실제 심사와 다를 수 있음",
    }


def _hit_to_dict(hit: RagHit) -> dict:
    return {
        "chunk_id": hit.chunk_id,
        "source_type": hit.source_type,
        "source_id": hit.source_id,
        "content": hit.content,
        "score": hit.score,
        "url": hit.url,
        "org": hit.org,
        "published_at": hit.published_at.isoformat() if hit.published_at else None,
    }


def _cite_rag_hits(_args: dict, result: str) -> list[dict]:
    """RAG 검색 결과 → signal 등급 인용."""
    hits = json.loads(result)
    return [
        {
            "grade": "signal",
            "source_type": hit["source_type"],
            "source_id": hit["source_id"],
            "url": hit["url"],
            "org": hit["org"],
        }
        for hit in hits
    ]


def _fact_citation(source: str, **extra: object) -> list[dict]:
    return [{"grade": "fact", "source": source, **extra}]


def build_tools(
    facts: RegionFactsPort,
    rag_search: RagSearchUseCase,
    finance: FinanceFactsPort,
    funding: FundingFactsPort,
) -> list[AgentTool]:
    """10종 도구를 조립한다 — 이름/분기는 registry(리스트) 하나로, if/elif 없이."""

    def run_get_region_metrics(args: dict) -> str:
        result = facts.metrics(args["region_code"], args["industry"])
        return json.dumps(result, ensure_ascii=False)

    def cite_get_region_metrics(args: dict, _result: str) -> list[dict]:
        return _fact_citation(
            "region_industry_metric",
            region_code=args["region_code"],
            industry=args["industry"],
        )

    def run_get_region_summary(args: dict) -> str:
        result = facts.summary(args["region_code"], args["industry_id"])
        return json.dumps(result, ensure_ascii=False)

    def cite_get_region_summary(args: dict, _result: str) -> list[dict]:
        return _fact_citation(
            "region_summary",
            region_code=args["region_code"],
            industry_id=args["industry_id"],
        )

    def run_get_neighborhood_profile(args: dict) -> str:
        result = facts.neighborhood_profile(args["region_code"])
        return json.dumps(result, ensure_ascii=False)

    def cite_get_neighborhood_profile(args: dict, _result: str) -> list[dict]:
        return _fact_citation("region_profile_quarter", region_code=args["region_code"])

    def run_get_population(args: dict) -> str:
        result = facts.population(args["region_code"])
        return json.dumps(result, ensure_ascii=False)

    def cite_get_population(args: dict, _result: str) -> list[dict]:
        return _fact_citation("population_stat", region_code=args["region_code"])

    def run_search_shocks(args: dict) -> str:
        events = facts.shocks(args.get("industry_id"), args["limit"])
        rates = facts.latest_rates()
        return json.dumps({"events": events, "latest_rates": rates}, ensure_ascii=False)

    def cite_search_shocks(_args: dict, result: str) -> list[dict]:
        parsed = json.loads(result)
        citations = [
            {"grade": "fact", "source": "shock_event", "event_id": e["event_id"], "url": e.get("source_url")}
            for e in parsed["events"]
        ]
        citations.append({"grade": "fact", "source": "interest_rate"})
        return citations

    def run_search_news(args: dict) -> str:
        hits = rag_search.search(args["query"], top_k=args.get("top_k", 5), source_type="news")
        return json.dumps([_hit_to_dict(h) for h in hits], ensure_ascii=False)

    def run_search_funding(args: dict) -> str:
        hits = rag_search.search(args["query"], top_k=args.get("top_k", 5), source_type="funding")
        return json.dumps([_hit_to_dict(h) for h in hits], ensure_ascii=False)

    def run_get_funding_candidates(args: dict) -> str:
        result = funding.candidates(
            args.get("industry_id"), args.get("external_funding_need"), args.get("stage")
        )
        return json.dumps(result, ensure_ascii=False)

    def cite_get_funding_candidates(_args: dict, result: str) -> list[dict]:
        """후보 공고는 원문 링크가 근거다 — RAG 신호가 아니라 결정론 필터 결과라 fact 등급."""
        parsed = json.loads(result)
        return [
            {"grade": "fact", "source": "funding_program", "title": c["title"], "url": c["url"]}
            for c in parsed["candidates"]
        ]

    def run_finance_simulation(args: dict) -> str:
        # 계산은 finance BC 엔진이 한다 — LLM은 표를 읽고 설명만 한다 (설계서 §6)
        return json.dumps(finance.simulate(args), ensure_ascii=False)

    def cite_finance_simulation(_args: dict, _result: str) -> list[dict]:
        return _fact_citation("finance_engine")

    def run_compare_rent_vs_buy(args: dict) -> str:
        annual_rate_pct = args.get("annual_rate_pct")
        if annual_rate_pct is None:
            annual_rate_pct = facts.latest_rates().get("loan_facility")
            if annual_rate_pct is None:
                return json.dumps(
                    {"error": "시설자금대출 금리 데이터가 없어 연금리를 지정해야 합니다"},
                    ensure_ascii=False,
                )
        result = compare_rent_vs_buy(
            monthly_rent_manwon=args["monthly_rent_manwon"],
            purchase_price_manwon=args["purchase_price_manwon"],
            equity_manwon=args["equity_manwon"],
            annual_rate_pct=annual_rate_pct,
        )
        return json.dumps(result, ensure_ascii=False)

    return [
        AgentTool(
            spec=LLMToolSpec(
                name="get_region_metrics",
                description="행정동×업종의 연도별 지표(점포수·폐업률·성장률)를 조회한다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "region_code": {"type": "string", "description": "행정동 코드"},
                        "industry": {"type": "string", "description": "업종 ID"},
                    },
                    "required": ["region_code", "industry"],
                },
            ),
            stage="market",
            run=run_get_region_metrics,
            cite=cite_get_region_metrics,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="get_region_summary",
                description="행정동×업종 요약 카드(최신 연도 점포수·폐업률·성장률)를 조회한다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "region_code": {"type": "string", "description": "행정동 코드"},
                        "industry_id": {"type": "string", "description": "업종 ID"},
                    },
                    "required": ["region_code", "industry_id"],
                },
            ),
            stage="market",
            run=run_get_region_summary,
            cite=cite_get_region_summary,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="get_neighborhood_profile",
                description=(
                    "행정동의 동네 유형·시간대 특성과 판정 근거, 유동인구 연령 구성, 상권 변화 지표, "
                    "집객시설 구성, 아파트 평균 시가를 조회한다. market 섹션 여섯 슬롯의 재료다."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "region_code": {"type": "string", "description": "행정동 코드"},
                    },
                    "required": ["region_code"],
                },
            ),
            stage="market",
            run=run_get_neighborhood_profile,
            cite=cite_get_neighborhood_profile,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="get_population",
                description="행정동의 최신 연령 분포와 학령(5~19세) 인구 합계를 조회한다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "region_code": {"type": "string", "description": "행정동 코드"},
                    },
                    "required": ["region_code"],
                },
            ),
            stage="market",
            run=run_get_population,
            cite=cite_get_population,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="search_shocks",
                description="업종(선택) 충격 이벤트 목록과 최신 금리를 조회한다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "industry_id": {"type": "string", "description": "업종 ID (생략 시 전체)"},
                        "limit": {"type": "integer", "description": "조회할 최대 건수"},
                    },
                    "required": ["limit"],
                },
            ),
            stage="shock",
            run=run_search_shocks,
            cite=cite_search_shocks,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="search_news",
                description="관련 뉴스 기사를 유사도 검색한다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 질의"},
                        "top_k": {"type": "integer", "description": "반환 개수"},
                    },
                    "required": ["query"],
                },
            ),
            stage="shock",
            run=run_search_news,
            cite=_cite_rag_hits,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="search_funding",
                description="관련 정책자금 공고를 유사도 검색한다(만료분 제외).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 질의"},
                        "top_k": {"type": "integer", "description": "반환 개수"},
                    },
                    "required": ["query"],
                },
            ),
            stage="funding",
            run=run_search_funding,
            cite=_cite_rag_hits,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="get_funding_candidates",
                description=(
                    "서울 창업자에게 해당할 수 있는 미만료 정책자금 공고를 규칙으로 걸러 상위 8건 돌려준다. "
                    "유사도 검색(search_funding)과 달리 지역·대상·마감을 확정적으로 판정한다. 자격 확정이 아니다."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "industry_id": {"type": "string", "description": "업종 ID (선택)"},
                        "external_funding_need": {
                            "type": "integer",
                            "description": "자기자본 외 조달 필요 금액(원, 선택) — 필터에는 쓰이지 않고 문장에 쓴다",
                        },
                        "stage": {
                            "type": "string",
                            "description": "pre(사업자등록 전) | registered(등록 후). 생략 가능",
                        },
                    },
                    "required": [],
                },
            ),
            stage="funding",
            run=run_get_funding_candidates,
            cite=cite_get_funding_candidates,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="run_finance_simulation",
                description=(
                    "창업 자금 계획을 결정론 엔진으로 계산한다 — 총 준비자금·자기자본 외 조달 필요·"
                    "희망대출 반영 후 부족액·손익분기 매출·시나리오 3·금리 스트레스 2. 원 단위 정수, 비율은 소수."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "deposit": {"type": "integer", "description": "보증금(원)"},
                        "key_money": {"type": "integer", "description": "권리금(원)"},
                        "interior_cost": {"type": "integer", "description": "인테리어 비용(원)"},
                        "equipment_cost": {"type": "integer", "description": "설비 비용(원)"},
                        "monthly_rent": {"type": "integer", "description": "월세(원)"},
                        "monthly_payroll": {"type": "integer", "description": "월 인건비(원)"},
                        "monthly_insurance": {"type": "integer", "description": "월 보험료(원)"},
                        "cost_ratio": {"type": "number", "description": "원가율(비율, 예 0.35)"},
                        "fee_ratio": {"type": "number", "description": "수수료율(비율, 예 0.03)"},
                        "equity": {"type": "integer", "description": "자기자본(원)"},
                        "desired_loan": {"type": "integer", "description": "희망 대출금(원)"},
                        "loan_rate": {"type": "number", "description": "대출 연금리(비율, 예 0.0405)"},
                        "expected_monthly_revenue": {"type": "integer", "description": "예상 월매출(원)"},
                    },
                    "required": ["deposit", "key_money", "interior_cost", "equipment_cost", "monthly_rent", "monthly_payroll", "monthly_insurance", "cost_ratio", "fee_ratio", "equity", "desired_loan", "loan_rate", "expected_monthly_revenue"],
                },
            ),
            # SSE agent_status 어휘는 market|shock|funding 셋뿐(프론트 AgentName 합집합) — 계산기는 funding에 속한다
            stage="funding",
            run=run_finance_simulation,
            cite=cite_finance_simulation,
        ),
        AgentTool(
            spec=LLMToolSpec(
                name="compare_rent_vs_buy",
                description="월세와 매입(대출) 비용을 비교한다. 연금리 생략 시 공시 시설자금대출 최신 금리를 자동 적용.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "monthly_rent_manwon": {"type": "number", "description": "월세(만원)"},
                        "purchase_price_manwon": {"type": "number", "description": "매입가(만원)"},
                        "equity_manwon": {"type": "number", "description": "자기자본(만원)"},
                        "annual_rate_pct": {"type": "number", "description": "연금리(%), 생략 가능"},
                    },
                    "required": ["monthly_rent_manwon", "purchase_price_manwon", "equity_manwon"],
                },
            ),
            stage="funding",
            run=run_compare_rent_vs_buy,
            cite=None,
        ),
    ]
