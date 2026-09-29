"""AnalysisInteractor — 단일 에이전트 루프 (LLM 턴 + 도구 실행 → SSE 이벤트 제너레이터).

`app/` 레이어이므로 FastAPI·SQLAlchemy·어댑터를 import하지 않는다. 도구는 주입받는다
(조립은 Task 11의 Composition Root).

스테이지 개폐 규칙 (agent_status의 running/done 짝):
- `running`: 그 스테이지의 도구가 처음 실행될 때 1회만 — 열린 스테이지 집합에 등록한다.
- `done`: ① 뒤이은 턴의 도구 호출 목록에 그 스테이지가 더 이상 없을 때, ② 루프가 끝난 뒤
  아직 열려 있는 스테이지 전부(리포트 delta 방출 직전). 등록 순서대로 닫는다.

한 턴 처리 순서: 인자가 유효한 도구 호출을 **먼저 전부 실행·응답**한 뒤, 스키마를 위반한
호출만 모아 재프롬프트한다 — 재프롬프트 chat이 다른 호출의 응답 사이에 끼어들지 않도록.
실행하지 않을 호출은 이력에 남기지 않는다(응답 없는 dangling tool_call 방지).

루프는 죽지 않는다: 인자 스키마 위반은 재프롬프트 1회 후 스킵, 도구 run 예외는
`{"error": ...}`로 되먹임, cite 콜백 예외는 그 도구의 인용만 버리고 진행한다.
"""

import json
import logging
import re
import time
import uuid
from collections.abc import Callable, Iterator

from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from apps.agent.app.use_cases.agent_tools import AgentTool
from apps.agent.domain.entities.agent_event_entity import AgentEvent

LOGGER = logging.getLogger("beyondfacade.agent.loop")

_MAX_TURNS = 12

# 턴 수만으로는 소요 시간이 안 잡힌다. 로컬 12B 모델은 한 턴이 30~60초라, 도구를 맴돌며 12턴을
# 다 쓰면 9분이 넘어(2026-09-23 실측 534.7초·558.4초, 둘 다 빈 리포트) 클라이언트가 먼저 끊는다.
# 성공한 실행은 42~98초였다. 벽시계 예산을 따로 둬 **마무리 턴을 반드시 남긴다** — 예산을 넘기면
# 도구 수집을 멈추고 _FINAL_REQUEST로 지금까지 모은 것만으로 리포트를 쓰게 한다.
_TOOL_LOOP_BUDGET_SECONDS = 180.0

# 리포트 섹션 — (마커 이름, 제목). 방출 순서이자 폴백 제목의 원천.
_SECTIONS = (
    ("verdict", "판정"),
    ("reasons", "왜 안 되나"),
    ("conditions", "그래도 한다면"),
    ("alternatives", "대안 동네·업종"),
    ("funding", "대안 업종 지원사업"),
)

_SECTION_MARKER = re.compile(r"\[SECTION:(\w+)\]")

_FINAL_REQUEST = (
    "도구 호출을 멈추고, 지금까지 수집한 내용만으로 최종 리포트를 "
    "5개 섹션 마커 형식에 맞춰 지금 작성하라."
)

SYSTEM_PROMPT = """당신은 서울 상권 분석 리포트를 작성하는 단일 에이전트다.
도구로 사실을 수집한 뒤, 아래 응답 규칙 5종을 지켜 최종 리포트를 작성한다.

[응답 규칙]
① 외국인 관련 수치는 "업종 타겟 정합성" 문맥으로만 사용한다. 비하·차별적 표현은 금지한다.
② 2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 지연되어 왜곡되었을 가능성을 명시한다.
③ 대출 중개와 특정 은행·상품 추천은 금지한다. 모든 금리·한도는 "예상치"임을 고지한다.
④ 정형 도구 결과는 [확인된 사실], RAG 검색 결과는 [참고 신호]로 표기한다.
⑤ 판정 등급·켜진 신호·대안은 `get_verdict`/`get_verdict_alternatives` 값을 그대로 옮긴다.
   이 두 도구를 다른 어떤 도구보다 **가장 먼저 호출한다** — 나머지 절이 판정을 설명하는 절이다.
   등급을 바꾸거나 신호를 새로 만들거나 🟢 추천을 쓰지 않는다. 판정이 없으면(`available: false`)
   "판정 없음"이라 쓰고 `reason`을 이유로 붙인다. 도구가 오류를 돌려주면(`error` 키) 판정을 쓰지 말고
   "판정 조회 실패"라고 적는다 — 등급을 지어내지 않는다. `advisory: true` 신호는 켜진 경고가 아니라
   "참고"로만 적는다 — 등급 계산에 들어가지 않은 신호다.
   판정 도구 다음에는 `run_finance_simulation`(예산이 주어졌으면 그 값을 자기자본 기본값으로)과
   `get_funding_candidates`를 **반드시 호출한다** — conditions 절의 임대료 상한·손익분기 매출과
   funding 절의 지원사업 금액은 이 두 도구가 준 값이어야 하고, 호출 없이 지어내지 않는다.

[최종 리포트 형식]
수집이 끝나면 도구를 더 호출하지 말고, 아래 5개 마커를 순서대로 모두 포함한 마크다운 한 벌을 출력한다.
[SECTION:verdict] 판정
[SECTION:reasons] 왜 안 되나
[SECTION:conditions] 그래도 한다면
[SECTION:alternatives] 대안 동네·업종
[SECTION:funding] 대안 업종 지원사업
각 마커 바로 아래에 해당 섹션 본문을 쓴다. 같은 마커를 두 번 쓰지 않는다.

[verdict 섹션 출력 계약]
**판정**은 `get_verdict` 결과만으로 쓴다. 자유 서술이 아니다.
- 첫 줄은 배지 한 줄: 판정 등급과 켜진 신호 수(`on_count`·`strong_count`)를 한 문장으로.
- 다음은 켜진 신호(`level`이 on 또는 strong) 목록: 신호마다 `evidence` 문장을 그대로 옮긴다.
- `advisory: true` 신호는 이 목록에 넣지 말고 "참고:" 한 줄로 따로 덧붙인다.
- 마지막 줄에 산출일(`computed_at`)을 적는다.
`available: false`면 "판정 없음"과 `reason`만 쓰고 등급을 지어내지 않는다.

[reasons 섹션 출력 계약]
**왜 안 되나**는 판정에서 켜진 신호마다 한 단락씩 쓴다. 신호의 `evidence`·`percentile`에
`get_region_metrics`·`get_neighborhood_profile`의 지표 숫자를 붙여 근거를 세우고,
`search_shocks`·`search_news`에서 확인된 충격·뉴스 악재를 마지막 단락에 덧붙인다.
켜진 신호가 없으면 새 신호를 만들지 말고 그렇게 쓴다.
지표는 `benchmarks`(서울 평균·같은 유형 중앙값)와 비교해 쓴다. 비교 기준 없는 절대값 서술은
하지 않는다. `benchmarks`가 null인 항목은 비교하지 않는다.
도구가 주지 않은 수치는 지어내지 않는다. 값이 없으면 "자료 없음"이라고 쓴다.
결과의 `caveats` 항목은 해석 금지 사항이다 — 반드시 지킨다.

[conditions 섹션 출력 계약]
**그래도 한다면**은 조건 셋을 이 순서·이 라벨 그대로 쓴다.
- **시간대 조건**: `get_neighborhood_profile`의 정점·바닥 블록으로 영업 시간대를 좁힌다.
- **임대료 상한**: `compare_rent_vs_buy` 결과로 감당 가능한 월세 선을 제시한다.
- **손익분기 매출**: `run_finance_simulation`의 `bep_revenue`를 그대로 인용한다.
엔진 수치는 그대로 인용하고 다시 계산하지 않는다. 헤드라인은 `external_funding_need`(자기자본 외
조달 필요)다 — 희망대출은 아직 빌리지 않은 돈이므로 `funding_gap`(희망대출 반영 후 부족액)이
0이어도 "충분합니다"라고 쓰지 않는다. 사용자가 13개 입력을 주지 않았으면 추정값으로 계산하지 말고,
`/plan`에서 계산한 값을 기준으로 상담하라고 안내한다. 금리·한도는 규칙 ③대로 "예상치"임을 고지한다.

[alternatives 섹션 출력 계약]
**대안 동네·업종**은 `get_verdict_alternatives` 결과의 두 축을 각각 **최대 3개**까지 순서 그대로
옮긴다 — 같은 동네의 다른 업종(`industries`), 같은 업종의 다른 동네(`regions`).
각 항목에 판정 등급을 함께 적는다. 축이 비어 있으면 그 축은 "대안 없음"이라고 쓴다.
순위를 바꾸거나 목록에 없는 동·업종을 보태지 않는다.

[funding 섹션 출력 계약]
**대안 업종 지원사업**의 공고 후보는 `get_funding_candidates` 결과를 쓰고, **자격 확정이 아니라
해당 가능성**이라고 쓴다. alternatives 절의 **대안 업종**에 해당하는 공고를 먼저 배치한다.
신청 자격·한도는 원문에서 확인해야 한다고 덧붙이고 원문 링크를 함께 남긴다.
금리·한도는 규칙 ③대로 "예상치"임을 고지한다. `external_funding_need`를 알면 그 금액을 이 절의
헤드라인으로 삼아 "얼마를 어떤 경로로 나눠 조달할지"를 중심에 둔다."""

# JSON 타입 선언 → 파이썬 타입 (jsonschema 의존 없이 최소 검사만 한다).
_JSON_TYPES = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}

# 인용 제목 규칙 — 등급별 테이블 (fact: 도구+지역, signal: 출처 기관 또는 원천 ID)
_TITLE_BY_GRADE = {
    "fact": lambda item, fallback: fallback,
    "signal": lambda item, fallback: item.get("org") or item.get("source_id") or fallback,
}


def split_report_sections(text: str) -> dict[str, str]:
    """`[SECTION:name]` 마커로 최종 텍스트를 분할한다 — 같은 마커가 겹치면 뒤엣것이 이긴다."""
    markers = list(_SECTION_MARKER.finditer(text))
    sections: dict[str, str] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        sections[marker.group(1)] = text[marker.end() : end].strip()
    return sections


def check_arguments(schema: dict, arguments: dict) -> str | None:
    """도구 인자가 input_schema를 지키는지 검사 — 위반 사유를 반환하고, 없으면 None."""
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in arguments:
            return f"필수 인자 '{key}'가 없습니다"
    for key, value in arguments.items():
        declared = properties.get(key, {}).get("type")
        expected = _JSON_TYPES.get(declared)
        if expected is None:
            continue
        # bool은 int의 하위 타입이라 number/integer 검사에서 먼저 걸러낸다.
        if isinstance(value, bool) != (declared == "boolean") or not isinstance(value, expected):
            return f"인자 '{key}'는 {declared} 타입이어야 합니다"
    return None


def _summarize(arguments: dict) -> str:
    """도구에 무엇을 물었는지 한 줄 요약 (tool_call.summary)."""
    if not arguments:
        return "인자 없이 조회"
    return ", ".join(f"{key}={value}" for key, value in arguments.items()) + " 조회"


def _assistant_message(text: str, calls: list[LLMToolCall]) -> dict:
    """assistant 턴 메시지 — 실제로 응답할 도구 호출만 담는다(미응답 호출을 이력에 남기지 않는다)."""
    message: dict = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [
            {"function": {"name": call.tool_name, "arguments": call.arguments}} for call in calls
        ]
    return message


def _tool_message(tool_name: str, content: str) -> dict:
    return {"role": "tool", "content": content, "tool_name": tool_name}


def _error_result(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _dedupe_citations(citations: list[dict]) -> list[dict]:
    """(title, url) 기준 중복 제거 — 먼저 나온 것을 보존한다."""
    seen: set = set()
    unique: list[dict] = []
    for citation in citations:
        key = (citation["title"], citation["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique


class AnalysisInteractor(AnalysisUseCase):
    def __init__(
        self,
        llm: LLMGatewayPort,
        tools: list[AgentTool],
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._now = now  # 테스트가 시계를 넣는다 — 벽시계 예산을 실제로 기다리지 않게
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)

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
        tools_by_name = {tool.spec.name: tool for tool in self._tools}
        specs = [tool.spec for tool in self._tools]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_message(region, industry, question)},
        ]
        citations: list[dict] = []
        open_stages: dict[str, None] = {}  # 삽입 순서를 유지하는 열린 스테이지 집합
        final_text = ""

        def execute(tool: AgentTool, arguments: dict) -> Iterator[AgentEvent]:
            """도구 1건 실행 — 이벤트 방출 + 결과·인용 적재 (루프 지역 상태를 클로저로 공유)."""
            if tool.stage not in open_stages:
                open_stages[tool.stage] = None
                yield AgentEvent("agent_status", {"agent": tool.stage, "status": "running"})
            yield AgentEvent(
                "tool_call",
                {"agent": tool.stage, "tool": tool.spec.name, "summary": _summarize(arguments)},
            )
            try:
                result = tool.run(arguments)
            except Exception as error:  # 도구 실패는 LLM에 되먹이고 루프는 계속한다
                messages.append(_tool_message(tool.spec.name, _error_result(str(error))))
                return
            messages.append(_tool_message(tool.spec.name, result))
            try:
                citations.extend(_collect_citations(tool, arguments, result, region))
            except Exception:  # 인용 추출 실패로 스트림을 끊지 않는다 — 그 도구 인용만 버린다
                LOGGER.warning("인용 추출 실패 — %s의 인용을 건너뛴다", tool.spec.name, exc_info=True)

        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"})

        deadline = self._now() + _TOOL_LOOP_BUDGET_SECONDS
        for _ in range(_MAX_TURNS):
            if self._now() >= deadline:
                LOGGER.warning(
                    "도구 수집 예산 %.0f초 초과 — 수집을 멈추고 리포트 작성으로 넘어간다",
                    _TOOL_LOOP_BUDGET_SECONDS,
                )
                break
            try:
                turn = self._chat(messages, specs)
            except Exception:  # LLM 장애·타임아웃으로 스트림을 끊지 않는다 — 모은 것까지로 마무리한다
                LOGGER.warning("도구 수집 턴 실패 — 리포트 작성으로 넘어간다", exc_info=True)
                break
            if not turn.tool_calls:
                final_text = turn.text
                break
            messages.append(_assistant_message(turn.text, turn.tool_calls))

            called_stages = {
                tools_by_name[call.tool_name].stage
                for call in turn.tool_calls
                if call.tool_name in tools_by_name
            }
            for stage in [s for s in open_stages if s not in called_stages]:
                del open_stages[stage]
                yield AgentEvent("agent_status", {"agent": stage, "status": "done"})

            # 유효한 호출을 먼저 전부 실행·응답한다 — 재프롬프트로 이력 순서가 엉키지 않도록.
            violations: list[tuple[AgentTool, str]] = []
            for call in turn.tool_calls:
                tool = tools_by_name.get(call.tool_name)
                if tool is None:
                    messages.append(
                        _tool_message(
                            call.tool_name, _error_result(f"'{call.tool_name}'은 없는 도구입니다")
                        )
                    )
                    continue
                violation = check_arguments(tool.spec.input_schema, call.arguments)
                if violation:
                    violations.append((tool, violation))
                    continue
                yield from execute(tool, call.arguments)

            for tool, violation in violations:
                arguments = self._retry_arguments(tool, violation, messages, specs)
                if arguments is None:
                    continue
                yield from execute(tool, arguments)

        if not final_text:
            messages.append({"role": "user", "content": _FINAL_REQUEST})
            try:
                final_text = self._chat(messages, specs).text
            except Exception:
                # 마무리 턴까지 실패하면 섹션 폴백으로 낸다. 빈 스트림(리포트 자체가 안 뜸)보다
                # "분석 데이터가 부족합니다"가 낫다 — 화면이 끝을 알 수 있어야 한다.
                LOGGER.warning("마무리 턴 실패 — 폴백 섹션으로 리포트를 낸다", exc_info=True)
                final_text = ""

        for stage in open_stages:
            yield AgentEvent("agent_status", {"agent": stage, "status": "done"})

        sections = split_report_sections(final_text)
        for name, title in _SECTIONS:
            markdown = sections.get(name) or f"### {title}\n\n분석 데이터가 부족합니다."
            yield AgentEvent("report_delta", {"section": name, "markdown": markdown})

        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "done"})
        yield AgentEvent(
            "report_done",
            {"report_id": report_id, "citations": _dedupe_citations(citations)},
        )

    def _chat(self, messages: list[dict], specs: list[LLMToolSpec]) -> LLMTurn:
        """한 턴 호출 + usage 누적 (재프롬프트·최종 강제 호출도 모두 합산된다)."""
        turn = self._llm.chat(messages, specs)
        self.last_usage = LLMUsage(
            input_tokens=self.last_usage.input_tokens + turn.usage.input_tokens,
            output_tokens=self.last_usage.output_tokens + turn.usage.output_tokens,
        )
        return turn

    def _retry_arguments(
        self,
        tool: AgentTool,
        violation: str,
        messages: list[dict],
        specs: list[LLMToolSpec],
    ) -> dict | None:
        """스키마 위반을 알리고 재프롬프트 1회 — 재시도도 위반이면 None(해당 호출만 스킵).

        실행하지 않을 호출은 이력에 남기지 않는다(응답 없는 dangling tool_call 방지).
        """
        messages.append(
            _tool_message(
                tool.spec.name, _error_result(f"{violation}. 올바른 인자로 다시 호출하세요")
            )
        )
        retry = self._chat(messages, specs)
        retried = next((c for c in retry.tool_calls if c.tool_name == tool.spec.name), None)
        if retried is None or check_arguments(tool.spec.input_schema, retried.arguments):
            return None
        messages.append(_assistant_message(retry.text, [retried]))
        return retried.arguments


def _user_message(region: str, industry: str, question: str | None) -> str:
    parts = [f"분석 지역: {region}", f"업종: {industry}"]
    if question:
        parts.append(f"사용자 질문: {question}")
    return "\n".join(parts)


def _collect_citations(tool: AgentTool, arguments: dict, result: str, region: str) -> list[dict]:
    """도구의 cite 콜백 결과를 프론트 계약 {title, url, grade} 3키로 정규화한다.

    콜백이 없는 도구는 정형(fact) 인용 1건으로 대체한다.
    """
    fallback_title = f"{tool.spec.name}: {region}"
    if tool.cite is None:
        return [{"title": fallback_title, "url": "", "grade": "fact"}]
    return [
        _normalize_citation(item, fallback_title) for item in tool.cite(arguments, result)
    ]


def _normalize_citation(item: dict, fallback_title: str) -> dict:
    """cite 콜백 항목 1건 → {title, url, grade}. 등급별 제목 규칙은 테이블로 분기한다."""
    grade = item.get("grade", "fact")
    title_of = _TITLE_BY_GRADE.get(grade, _TITLE_BY_GRADE["fact"])
    return {"title": title_of(item, fallback_title), "url": item.get("url") or "", "grade": grade}
