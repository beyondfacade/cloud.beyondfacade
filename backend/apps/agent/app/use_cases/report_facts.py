"""ReportFactsCollector — LLM을 부르기 전에 리포트가 쓸 사실을 코드가 먼저 모은다 (설계서 §3-1).

사실은 코드가 모으고 LLM은 글만 쓴다. 같은 dict가 `facts` SSE 이벤트(프론트가 즉시 그림을 그린다)와
LLM 첫 메시지의 `[FACTS]`로 동시에 나간다.

항목마다 try/except로 격리한다 — 하나가 실패해도 나머지 그림은 뜬다. 실패한 자리는
`{"available": false, "reason": ...}`이라 프론트가 "자료 없음" 한 줄로 대신 그린다.

`app/` 레이어라 어댑터·타 BC를 직접 import하지 않는다 — 포트만 받는다.
"""

from collections.abc import Callable

from apps.agent.app.ports.output.agent_port import (
    FundingFactsPort,
    RegionFactsPort,
    VerdictFactsPort,
)
from apps.agent.app.use_cases.agent_tools import hit_to_dict
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase

# 프론트 시각 자료와 1:1로 대응하는 키 (설계서 §5 계약 표) — 순서도 계약이다.
FACTS_KEYS = (
    "region",
    "verdict",
    "alternatives",
    "profile",
    "hour_gap",
    "commerce_change",
    "metrics_history",
    "population",
    "shocks",
    "news",
    "funding_candidates",
    "budget",
)

_SHOCK_LIMIT = 5
_NEWS_TOP_K = 5


def _isolated(call: Callable[[], object]) -> object:
    """항목 1건 수집 — 실패는 값으로 바꾼다(전부 아니면 무, 가 아니다)."""
    try:
        return call()
    except Exception as error:
        return {"available": False, "reason": f"{type(error).__name__}: {error}"}


class ReportFactsCollector:
    def __init__(
        self,
        region_facts: RegionFactsPort,
        verdict_facts: VerdictFactsPort,
        funding_facts: FundingFactsPort,
        news_search: RagSearchUseCase,
    ) -> None:
        self._region_facts = region_facts
        self._verdict_facts = verdict_facts
        self._funding_facts = funding_facts
        self._news_search = news_search

    def collect(self, region: str, industry: str, budget: int | None = None) -> dict:
        """§5 계약 표의 12키를 모은 JSON 직렬화 가능한 dict."""
        region_info = self._region_info(region, industry)
        return {
            "region": region_info,
            "verdict": _isolated(lambda: self._verdict_facts.verdict(region, industry)),
            "alternatives": _isolated(
                lambda: self._verdict_facts.alternatives(region, industry)
            ),
            "profile": _isolated(lambda: self._region_facts.neighborhood_profile(region)),
            "hour_gap": _isolated(lambda: self._region_facts.hour_gap(region, industry)),
            "commerce_change": _isolated(
                lambda: self._region_facts.commerce_change_detail(region)
            ),
            "metrics_history": _isolated(
                lambda: self._region_facts.metrics_history(region, industry)
            ),
            "population": _isolated(lambda: self._region_facts.population(region)),
            "shocks": _isolated(lambda: self._region_facts.shocks(industry, _SHOCK_LIMIT)),
            "news": _isolated(lambda: self._news(region_info)),
            "funding_candidates": _isolated(
                lambda: self._funding_facts.candidates(industry, None, None)
            ),
            "budget": budget,
        }

    def _region_info(self, region: str, industry: str) -> dict:
        """동 이름·업종명 — 요약 조회가 실패해도 코드만으로 나머지 수집을 이어간다."""
        summary = _isolated(lambda: self._region_facts.summary(region, industry))
        return {
            "code": region,
            "name": summary.get("name"),
            "industry_id": industry,
            "industry_name": summary.get("industry_name"),
        }

    def _news(self, region_info: dict) -> list[dict]:
        """동 이름 + 업종명으로 뉴스를 찾는다 — 이름을 못 얻었으면 코드로라도 찾는다."""
        name = region_info["name"] or region_info["code"]
        industry_name = region_info["industry_name"] or region_info["industry_id"]
        hits = self._news_search.search(
            f"{name} {industry_name}", top_k=_NEWS_TOP_K, source_type="news"
        )
        return [hit_to_dict(hit) for hit in hits]
