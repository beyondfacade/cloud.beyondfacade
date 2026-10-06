"""ReportFactsCollector — LLM을 부르기 전에 리포트가 쓸 사실을 코드가 먼저 모은다 (설계서 §3-1).

사실은 코드가 모으고 LLM은 글만 쓴다. 같은 dict가 `facts` SSE 이벤트(프론트가 즉시 그림을 그린다)와
LLM 첫 메시지의 `[FACTS]`로 동시에 나간다.

14항목을 **동시에** 조회한다 — 항목마다 제 세션(`session_scope`)을 여는 독립 조회라 서로 기다릴
이유가 없다. 직렬로 돌면 가장 느린 항목이 전체 수집 시간을 결정한다.

뉴스(`news`)는 원문 링크 목록이다 — 네이버 검색 결과라 본문 절·LLM 입력에 넣지 않고 화면 링크로만 쓴다.

항목마다 예외를 격리한다 — 하나가 실패해도 나머지 그림은 뜬다. 실패한 자리는
`{"available": false, "reason": ...}`이라 프론트가 "자료 없음" 한 줄로 대신 그린다.

`app/` 레이어라 어댑터·타 BC를 직접 import하지 않는다 — 포트만 받는다.
"""

import logging
import re
from concurrent.futures import Future, ThreadPoolExecutor

from apps.agent.app.ports.output.agent_port import (
    EventAnalogFactsPort,
    FinanceFactsPort,
    FundingFactsPort,
    NewsLinksPort,
    QuestionBudgetPort,
    RegionFactsPort,
    VerdictFactsPort,
)
from apps.agent.domain.services.analog_sentences import with_sentences

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
    "analogs",
    "news",
    "funding_candidates",
    "budget",
    "finance",
)

_SHOCK_LIMIT = 5
_NEWS_LIMIT = 3
# 동 이름 꼬리(번호·"제"·"가"·"동") — 남은 어간이 기사에 나오면 이 동 기사로 본다(상도제1동→상도, 종로1.2.3.4가동→종로)
_DONG_SUFFIX = re.compile(r"(?:제?\d+(?:\.\d+)*가?동|동)$")

# SQLAlchemy 기본 풀은 5+10이다 — 12칸으로 열면 12개 세션이 동시에 풀을 긁는다.
_MAX_WORKERS = 6


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
        news_links: NewsLinksPort,
        analog_facts: EventAnalogFactsPort | None = None,
        finance_facts: FinanceFactsPort | None = None,
        question_budget: QuestionBudgetPort | None = None,
    ) -> None:
        self._region_facts = region_facts
        self._verdict_facts = verdict_facts
        self._funding_facts = funding_facts
        self._news_links = news_links
        self._analog_facts = analog_facts
        self._finance_facts = finance_facts
        self._question_budget = question_budget

    def collect(
        self, region: str, industry: str, budget: int | None = None, question: str | None = None
    ) -> dict:
        """§5 계약 표의 14키를 모은 JSON 직렬화 가능한 dict (키 순서도 계약)."""
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            # region을 **가장 먼저** 넣는다 — 큐가 FIFO라 첫 워커가 반드시 집어 간다.
            region_future = pool.submit(self._region_info, region, industry)
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
                "analogs": pool.submit(self._analogs, industry, question),
                "funding_candidates": pool.submit(self._funding, industry, region),
                "finance": pool.submit(self._finance, region, industry),
                # 뉴스 질의는 동 이름을 쓴다 — 워커가 region future를 기다리므로 **맨 뒤**에
                # 넣는다. 앞선 항목이 워커를 다 채워도 region은 이미 실행 중이라 굶지 않는다.
                "news": pool.submit(self._news, region_future),
            }
            values: dict[str, object] = {key: _resolve(f) for key, f in futures.items()}
        values["budget"] = budget if budget is not None else self._question_budget_of(question)
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

    def _analogs(self, industry: str, question: str | None) -> dict:
        if self._analog_facts is None:
            return {"available": False, "reason": "유사 사례 조회가 연결되지 않았습니다"}
        return with_sentences(self._analog_facts.analogs(industry, question))

    def _funding(self, industry: str, region: str) -> list[dict]:
        """공고 목록만 남긴다 — 프론트 계약은 배열이다 (설계서 §3-1). 다른 구 전용 공고는 빠져 온다.

        되돌려받는 요청 값(`industry_id`·`stage`)과 `disclaimer`는 버린다 — 앞의 둘은 호출부가
        이미 알고, 면책 문구는 funding 절 프롬프트 계약이 이미 갖는다.
        `target`은 **넣지 않는다** — 원천의 분야(`field_category`)는 대상이 아니다("대상: 금융"은
        거짓말이다). 프론트는 `target`이 없으면 '대상' 줄을 지운다.
        """
        return self._funding_facts.candidates(industry, None, None, region)["candidates"]

    def _finance(self, region: str, industry: str) -> dict:
        if self._finance_facts is None:
            return {"available": False, "reason": "자금 계획 프리필이 연결되지 않았습니다"}
        return self._finance_facts.prefill(region, industry)

    def _question_budget_of(self, question: str | None) -> int | None:
        """폼 예산이 없을 때만 — 질문 속 금액(관문과 같은 규칙)."""
        if not question or self._question_budget is None:
            return None
        return self._question_budget.parse(question)

    def _news(self, region_future: Future) -> list[dict]:
        """동 이름이 나온 최근 기사의 원문 링크. 이름을 못 얻었으면(코드로 메운 자리) 찾지 않는다."""
        region_info = region_future.result()
        base = _DONG_SUFFIX.sub("", region_info["name"])
        if region_info["name"] == region_info["code"] or len(base) < 2:
            return []
        return self._news_links.mentioning(base, _NEWS_LIMIT)
