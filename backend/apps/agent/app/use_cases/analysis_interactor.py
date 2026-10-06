"""AnalysisInteractor — 리포트 SSE 이벤트 제너레이터 (사실은 코드, 해석은 LLM 한 단락).

설계서 docs/superpowers/specs/2026-10-05-report-code-first-design.md.
`app/` 레이어이므로 FastAPI·SQLAlchemy·어댑터를 import하지 않는다.

순서: 사실 수집(`facts`) → 질문이 있으면 코드 직접 답(`answer_lead`)이 6개 절보다 먼저 → 코드가 facts로 쓴 6개 절을 곧바로 `report_delta`로 → LLM 해석(`answer`) 한 단락을
끝까지 모아 가드(링크 제거·판정 모순 검사·숫자 문장 삭제)를 거쳐 한 번에 → `report_done`.
가드에 걸리거나 호출이 실패하면 다음 모델(`retry_llm`)로, 그래도 안 되면 코드 한 줄(`ANSWER_FALLBACK`)로 맺는다.
자료 부족 동네(`scarcity`)는 LLM을 부르지 않는다 — 해석은 자료 부족만 밝히는 코드 첫 문장(`scarce_lead`)뿐이다.
도구 루프는 없다 — 평가 252회에서 도구 호출 0회였고, 자금 계획은 별도 화면이다.
"""

import logging
import uuid
from collections.abc import Iterator

from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import LLMGatewayPort, LLMUsage
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.question_answer import answer_lead
from apps.agent.domain.services.question_topic import QuestionTopic, classify
from apps.agent.domain.services.report_guards import guard_answer
from apps.agent.domain.services.report_sections import (
    SECTION_TITLES,
    alternatives_pointer,
    build_sections,
    scarce_lead,
    scarcity,
)
from apps.agent.domain.services.section_stream import concat_sections

LOGGER = logging.getLogger("beyondfacade.agent.loop")

ANSWER_FALLBACK = "질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요."

# 사람 검수 4차(2026-10-06) "답변이 사용자에게 친절하지 않다" — 쉽게 풀어 쓰되 유치하지 않게(중고등학생 눈높이)
_PERSONA = """

[말투]
- 독자는 창업을 처음 알아보는 사람이다. 중고등학생도 한 번 읽고 이해할 수 있게 쓴다.
  다만 어린아이에게 말하듯 쓰지 않는다 — 감탄사·이모지·지나친 비유는 쓰지 않는다.
- "~습니다"체로, 옆에서 차분히 설명해 주는 선배처럼 쓴다. 겁을 주거나 부풀리지 않는다.
- 본문의 전문 용어(순유출, 생존 절벽, 조기 폐업, 포화, 상권변화지표, 경고 신호 등)를 쓰면 바로 뒤에 쉬운 말로 풀어 쓴다.
  예: "순유출, 즉 새로 여는 가게보다 문 닫는 가게가 더 많다는 뜻입니다."
- 한 문장에는 한 가지 내용만 담고 짧게 쓴다.
- 쉽게 쓰더라도 결론은 흐리지 않는다 — 판정과 직접 답의 방향은 그대로 전한다."""

_COMMON_RULES = _PERSONA + """

[내용 규칙]
- 제목·목록·표·굵은 글씨를 쓰지 않는다.
- 숫자를 쓰지 않는다 — 아라비아 숫자는 한 글자도 쓰지 않는다. 숫자는 본문이 범위와 함께 보여 준다.
  링크·공고 번호도 쓰지 않는다. 다만 동 이름은 본문에 적힌 그대로 쓴다(예: "역삼1동", "성수2가제1동") —
  동 이름 속 숫자를 한글로 풀어 쓰지 않는다.
- 판정 등급을 바꾸거나 새로 매기지 않는다. 본문에 없는 사실을 보태지 않는다.
- 본문이 "자료 부족"이라고 한 곳은 추정으로 메우지 않고 "자료가 부족해 판단할 수 없다"고 말한다.
- 뉴스는 [참고 신호]라고 밝히고만 쓴다. 뉴스로 판정이나 결론을 바꾸지 않는다.

[응답 규칙]
① 외국인 관련 내용은 업종 타깃 정합성 문맥으로만 쓴다. 비하·차별 표현은 금지한다.
② 코로나 재난지원 시기(재난지원금·손실보상으로 폐업이 늦춰졌을 수 있는 해)의 폐업률은 왜곡됐을 수 있음을 감안한다.
③ 대출 중개와 특정 은행·상품 추천은 금지한다. 금리·한도를 말하면 "예상치"라고 밝힌다."""

SYSTEM_PROMPT = """당신은 서울 창업 경고 리포트 맨 위의 "해석" 한 단락을 쓴다.
사용자 메시지에 총평 요청과, 화면에 이미 나간 리포트 본문 6개 절이 주어진다.
본문은 코드가 사실에서 쓴 글이다 — 본문만 근거로 삼는다.

[출력 규칙]
- 3~5문장, 한 단락. 이 동네에서 이 업종을 한다면 먼저 볼 것을 총평한다.""" + _COMMON_RULES

QUESTION_SYSTEM_PROMPT = """당신은 서울 창업 경고 리포트 맨 위 "질문에 대한 답" 상자의 해석 단락을 쓴다.
사용자 메시지에 질문, 질문 유형, 화면에 이미 나간 직접 답(첫 문장)과 근거, 리포트 본문 6개 절이 주어진다.
직접 답·근거·본문은 코드가 사실에서 쓴 글이다 — 이것만 근거로 삼는다.

[출력 규칙]
- 2~3문장, 한 단락. 직접 답이 왜 그런지 본문을 근거로 해석한다. 직접 답을 되풀이하지 않는다.
- 직접 답의 결론을 뒤집거나 흐리지 않는다(예: "권하지 않는다"를 "해볼 만하다"로).""" + _COMMON_RULES

LEAD_FALLBACK = "해석을 만들지 못했습니다. 위 답과 아래 사실을 직접 확인해 주세요."
TOPIC_NAMES = {
    "loan": "대출",
    "budget": "예산",
    "hours": "시간대",
    "competition": "경쟁",
    "customers": "대상 고객",
    "covid": "코로나",
    "general": "일반(이 자리 괜찮은가)",
}

_NO_QUESTION = "질문 없음 — 이 동네에서 이 업종을 한다면 먼저 볼 것을 총평하라."


def answer_message(
    facts: dict,
    question: str | None,
    sections: dict[str, str],
    topic: QuestionTopic | None = None,
    lead: str | None = None,
) -> str:
    """해석 LLM의 사용자 메시지 — 질문(과 유형·직접 답)과 화면에 나간 6개 절 그대로. 원본 facts JSON은 넘기지 않는다(설계서 §5)."""
    region = facts.get("region") or {}
    head = [
        f"분석 지역: {region.get('name')} / 업종: {region.get('industry_name')}",
        f"사용자 질문: {question}" if question else _NO_QUESTION,
    ]
    if lead:
        head += [f"질문 유형: {TOPIC_NAMES[topic.kind]}", "[이미 화면에 나간 직접 답과 근거]", lead]
    return "\n".join([*head, "[리포트 본문]", concat_sections(sections.items(), order=SECTION_TITLES)])


def region_names(facts: dict) -> list[str]:
    """분석 동과 대안 동 이름 — 동 이름에 숫자가 든다("상계3.4동"). 해석 숫자 가드가 이 숫자는 세지 않는다."""
    region = facts.get("region") or {}
    regions = (facts.get("alternatives") or {}).get("regions") or []
    return [n for n in (region.get("name"), *(r.get("region_name") for r in regions)) if n]


def _news_citations(news: object) -> list[dict]:
    """facts.news → 참고 신호 인용 {title, url, grade}. 제목은 기사 첫 줄, 링크 없는 기사는 뺀다(같은 링크는 한 번).

    수집이 실패한 자리는 `{"available": False, ...}` dict라 목록일 때만 읽는다.
    """
    citations: dict[str, dict] = {}
    for hit in news if isinstance(news, list) else []:
        url = hit.get("url")
        if url:
            title = (hit.get("content") or "").split("\n")[0] or url
            citations.setdefault(url, {"title": title, "url": url, "grade": "signal"})
    return list(citations.values())


class AnalysisInteractor(AnalysisUseCase):
    def __init__(
        self,
        llm: LLMGatewayPort,
        facts: ReportFactsCollector,
        budget: int | None = None,
        retry_llm: LLMGatewayPort | None = None,
    ) -> None:
        self._llm = llm
        self._facts = facts
        self._budget = budget  # facts 수집에 그대로 넘긴다(facts.budget)
        self._retry_llm = retry_llm  # 해석이 가드에 걸리거나 호출이 실패하면 다음 모델 (운영 hybrid: 로컬)
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)
        # 직전 실행의 해석 시도 기록(모델별 원문·지운 문장 수·링크 수·모순·오류) — 벤치가 남겨 채점한다
        self.last_answer_attempts: list[dict] = []

    def myself(self) -> dict:
        return {
            "analysis_id": "myself",
            "region_code": "myself",
            "industry": "myself",
            "model": getattr(self._llm, "model_name", "gemma3"),
        }

    def run(self, region: str, industry: str, question: str | None) -> Iterator[AgentEvent]:
        report_id = uuid.uuid4().hex
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)
        self.last_answer_attempts = []
        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"})

        yield AgentEvent("agent_status", {"agent": "facts", "status": "running"})
        facts = self._facts.collect(region, industry, self._budget, question)
        yield AgentEvent("facts", {"facts": facts})  # 프론트 계약은 중첩이다
        yield AgentEvent("agent_status", {"agent": "facts", "status": "done"})

        yield AgentEvent("agent_status", {"agent": "writer", "status": "running"})
        sections = build_sections(facts)
        topic = classify(question)
        lead = answer_lead(facts, topic) if topic is not None and scarcity(facts) is None else None
        if lead is not None:  # 직접 답은 코드라 사실이 모이자마자 맨 먼저 나간다
            yield AgentEvent("report_delta", {"section": "answer_lead", "markdown": lead})
        for name, markdown in sections.items():  # 본문은 사실이 모이자마자 나간다
            yield AgentEvent("report_delta", {"section": name, "markdown": markdown})
        answer = self._answer(facts, question, sections, topic, lead)
        yield AgentEvent("report_delta", {"section": "answer", "markdown": answer})
        yield AgentEvent("agent_status", {"agent": "writer", "status": "done"})
        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "done"})
        yield AgentEvent("report_done", {"report_id": report_id, "citations": _news_citations(facts.get("news"))})

    def _answer(
        self, facts: dict, question: str | None, sections: dict[str, str], topic: QuestionTopic | None, lead: str | None
    ) -> str:
        """해석 한 단락 — 자료 부족 동네면 코드 첫 문장만(판단은 사용자에게), 아니면 모델을 차례로 시도해
        가드를 통과한 첫 단락, 없으면 코드 한 줄."""
        missing = scarcity(facts)
        if missing is not None:
            return scarce_lead(facts, missing)
        messages = [
            {"role": "system", "content": QUESTION_SYSTEM_PROMPT if lead else SYSTEM_PROMPT},
            {"role": "user", "content": answer_message(facts, question, sections, topic, lead)},
        ]
        names = region_names(facts)
        hour_sales_known = bool((facts.get("hour_gap") or {}).get("available"))
        pointer = alternatives_pointer(facts)
        for llm in self._answer_models():
            answer = self._attempt(llm, messages, facts.get("verdict"), names, hour_sales_known)
            if answer:
                return f"{answer} {pointer}" if pointer else answer
        fallback = LEAD_FALLBACK if lead else ANSWER_FALLBACK
        return f"{fallback} {pointer}" if pointer else fallback

    def _answer_models(self) -> Iterator[LLMGatewayPort]:
        """시도할 모델 — 첫 모델이 실제로 답한 모델과 같은 다음 모델은 건너뛴다(온도 0이라 같은 답이다).

        hybrid는 Gemini 장애 때 이미 로컬로 내려가 `model_name`이 로컬 이름이 된다 — 그래서 첫 시도 뒤에 비교한다.
        """
        yield self._llm
        if self._retry_llm is not None and self._retry_llm.model_name != self._llm.model_name:
            yield self._retry_llm

    def _attempt(
        self, llm: LLMGatewayPort, messages: list[dict], verdict: dict | None, names: list[str], hour_sales_known: bool
    ) -> str | None:
        """한 모델 1회 — 가드를 통과한 단락, 아니면 None. 시도마다 기록을 남긴다."""
        try:
            turn = llm.chat(messages, [])
        except Exception as error:  # 장애로 리포트를 끊지 않는다 — 다음 모델 또는 코드 한 줄로 맺는다
            LOGGER.warning("해석 생성 실패 — %s: %s", llm.model_name, type(error).__name__)
            self.last_answer_attempts.append({"model": llm.model_name, "error": f"{type(error).__name__}: {error}"})
            return None
        self._accumulate(turn.usage)
        guarded = guard_answer(turn.text, verdict, names, hour_sales_known)
        self.last_answer_attempts.append(
            {
                "model": llm.model_name,
                "raw": turn.text,
                "removed_sentences": guarded.removed_sentences,
                "hour_sales_removed": guarded.hour_sales_removed,
                "links_stripped": guarded.links_stripped,
                "contradiction": guarded.contradiction,
            }
        )
        if guarded.contradiction:
            LOGGER.info("해석이 판정과 모순 — %s: %s", llm.model_name, guarded.contradiction[:60])
        return guarded.text if guarded.ok else None

    def _accumulate(self, usage: LLMUsage) -> None:
        self.last_usage = LLMUsage(
            input_tokens=self.last_usage.input_tokens + usage.input_tokens,
            output_tokens=self.last_usage.output_tokens + usage.output_tokens,
        )
