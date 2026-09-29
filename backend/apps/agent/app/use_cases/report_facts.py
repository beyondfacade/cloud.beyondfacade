"""ReportFactsCollector — LLM을 부르기 전에 리포트가 쓸 사실을 코드가 먼저 모은다 (설계서 §3-1).

사실은 코드가 모으고 LLM은 글만 쓴다. 같은 dict가 `facts` SSE 이벤트(프론트가 즉시 그림을 그린다)와
LLM 첫 메시지의 `[FACTS]`로 동시에 나간다.

12항목을 **동시에** 조회한다 — 항목마다 제 세션(`session_scope`)을 여는 독립 조회라 서로 기다릴
이유가 없다. 직렬로 돌면 가장 느린 항목(뉴스 RAG 임베딩)이 전체 수집 시간을 결정한다.

항목마다 예외를 격리한다 — 하나가 실패해도 나머지 그림은 뜬다. 실패한 자리는
`{"available": false, "reason": ...}`이라 프론트가 "자료 없음" 한 줄로 대신 그린다.

`app/` 레이어라 어댑터·타 BC를 직접 import하지 않는다 — 포트만 받는다.
"""

import logging
from concurrent.futures import Future, ThreadPoolExecutor

from apps.agent.app.ports.output.agent_port import (
    FundingFactsPort,
    RegionFactsPort,
    VerdictFactsPort,
)
from apps.agent.app.use_cases.agent_tools import hit_to_dict
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase

LOGGER = logging.getLogger("beyondfacade.agent.facts")

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


def _resolve(future: Future) -> object:
    """항목 1건 회수 — 실패는 값으로 바꾼다(전부 아니면 무, 가 아니다)."""
    try:
        return future.result()
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
        """§5 계약 표의 12키를 모은 JSON 직렬화 가능한 dict (키 순서도 계약)."""
        with ThreadPoolExecutor(max_workers=len(FACTS_KEYS)) as pool:
            region_future = pool.submit(self._region_info, region, industry)
            # 뉴스 질의는 동 이름·업종명을 쓴다 — 워커가 그 future를 기다린다(풀이 12칸이라 굶지 않는다)
            futures: dict[str, Future] = {
                "region": region_future,
                "verdict": pool.submit(self._verdict_facts.verdict, region, industry),
                "alternatives": pool.submit(self._verdict_facts.alternatives, region, industry),
                "profile": pool.submit(self._region_facts.neighborhood_profile, region),
                "hour_gap": pool.submit(self._region_facts.hour_gap, region, industry),
                "commerce_change": pool.submit(
                    self._region_facts.commerce_change_detail, region
                ),
                "metrics_history": pool.submit(
                    self._region_facts.metrics_history, region, industry
                ),
                "population": pool.submit(self._region_facts.population, region),
                "shocks": pool.submit(self._shocks, industry),
                "news": pool.submit(self._news, region_future),
                "funding_candidates": pool.submit(
                    self._funding_facts.candidates, industry, None, None
                ),
            }
            values: dict[str, object] = {key: _resolve(f) for key, f in futures.items()}
        values["budget"] = budget
        return {key: values[key] for key in FACTS_KEYS}

    def _region_info(self, region: str, industry: str) -> dict:
        """동 이름·업종명 — 조회가 실패해도 코드 문자열로 메운다(프론트는 문자열로 읽는다)."""
        try:
            summary = self._region_facts.summary(region, industry)
        except Exception:
            LOGGER.warning("요약 조회 실패 — 이름 자리를 코드로 메운다", exc_info=True)
            summary = {}
        return {
            "code": region,
            "name": summary.get("name") or region,
            "industry_id": industry,
            "industry_name": summary.get("industry_name") or industry,
        }

    def _shocks(self, industry: str) -> list[dict]:
        """업종 충격이 없으면(한식 등 원천에 영향 행이 없는 업종) 전 업종 공통 충격으로 되돌린다.

        어느 쪽인지는 `industry_specific`으로 구분한다 — 공통 충격을 업종 악재로 읽으면 안 된다.
        """
        events = self._region_facts.shocks(industry, _SHOCK_LIMIT)
        if events:
            return [{**event, "industry_specific": True} for event in events]
        return [
            {**event, "industry_specific": False}
            for event in self._region_facts.shocks(None, _SHOCK_LIMIT)
        ]

    def _news(self, region_future: Future) -> list[dict]:
        """동 이름 + 업종명으로 뉴스를 찾는다."""
        region_info = region_future.result()
        hits = self._news_search.search(
            f"{region_info['name']} {region_info['industry_name']}",
            top_k=_NEWS_TOP_K,
            source_type="news",
        )
        return [hit_to_dict(hit) for hit in hits]
