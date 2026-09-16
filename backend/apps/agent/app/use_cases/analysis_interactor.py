"""AnalysisInteractor — 단일 에이전트 루프 (LLM 턴 + 도구 실행 → SSE 이벤트 제너레이터).

`app/` 레이어이므로 FastAPI·SQLAlchemy·어댑터를 import하지 않는다. 도구는 주입받는다
(조립은 Task 11의 Composition Root).

스테이지 개폐 규칙 (agent_status의 running/done 짝):
- `running`: 그 스테이지의 도구가 처음 실행될 때 1회만 — 열린 스테이지 집합에 등록한다.
- `done`: ① 뒤이은 턴의 도구 호출 목록에 그 스테이지가 더 이상 없을 때, ② 루프가 끝난 뒤
  아직 열려 있는 스테이지 전부(리포트 delta 방출 직전). 등록 순서대로 닫는다.

루프는 죽지 않는다: 도구 인자가 스키마를 위반하면 재프롬프트 1회 후 스킵하고,
도구 run이 예외를 던지면 `{"error": ...}`를 결과로 되먹인 뒤 계속 진행한다.
"""

import json
import re
import uuid
from collections.abc import Iterator

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

_MAX_TURNS = 12

# 리포트 섹션 — (마커 이름, 제목). 방출 순서이자 폴백 제목의 원천.
_SECTIONS = (
    ("verdict", "종합 판정"),
    ("market", "상권 기초체력"),
    ("shock", "충격 취약도"),
    ("funding", "자금 조달"),
    ("calculator", "비용 계산"),
)

_SECTION_MARKER = re.compile(r"\[SECTION:(\w+)\]")

_FINAL_REQUEST = (
    "도구 호출을 멈추고, 지금까지 수집한 내용만으로 최종 리포트를 "
    "5개 섹션 마커 형식에 맞춰 지금 작성하라."
)

SYSTEM_PROMPT = """당신은 서울 상권 분석 리포트를 작성하는 단일 에이전트다.
도구로 사실을 수집한 뒤, 아래 응답 규칙 4종을 지켜 최종 리포트를 작성한다.

[응답 규칙]
① 외국인 관련 수치는 "업종 타겟 정합성" 문맥으로만 사용한다. 비하·차별적 표현은 금지한다.
② 2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 지연되어 왜곡되었을 가능성을 명시한다.
③ 대출 중개와 특정 은행·상품 추천은 금지한다. 모든 금리·한도는 "예상치"임을 고지한다.
④ 정형 도구 결과는 [확인된 사실], RAG 검색 결과는 [참고 신호]로 표기한다.

[최종 리포트 형식]
수집이 끝나면 도구를 더 호출하지 말고, 아래 5개 마커를 순서대로 모두 포함한 마크다운 한 벌을 출력한다.
[SECTION:verdict] 종합 판정
[SECTION:market] 상권 기초체력
[SECTION:shock] 충격 취약도
[SECTION:funding] 자금 조달
[SECTION:calculator] 비용 계산
각 마커 바로 아래에 해당 섹션 본문을 쓴다. 같은 마커를 두 번 쓰지 않는다."""

# JSON 타입 선언 → 파이썬 타입 (jsonschema 의존 없이 최소 검사만 한다).
_JSON_TYPES = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
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


def _assistant_message(turn: LLMTurn) -> dict:
    message: dict = {"role": "assistant", "content": turn.text}
    if turn.tool_calls:
        message["tool_calls"] = [
            {"function": {"name": call.tool_name, "arguments": call.arguments}}
            for call in turn.tool_calls
        ]
    return message


def _tool_message(tool_name: str, content: str) -> dict:
    return {"role": "tool", "content": content, "tool_name": tool_name}


def _error_result(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _dedupe_citations(citations: list[dict]) -> list[dict]:
    """(title, url) 기준 중복 제거 — 둘 다 없는 인용(정형 도구 cite 콜백)은 내용 전체로 식별한다."""
    seen: set = set()
    unique: list[dict] = []
    for citation in citations:
        key = (citation.get("title"), citation.get("url"))
        if key == (None, None):
            key = json.dumps(citation, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique


class AnalysisInteractor(AnalysisUseCase):
    def __init__(self, llm: LLMGatewayPort, tools: list[AgentTool]) -> None:
        self._llm = llm
        self._tools = tools
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)

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

        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"})

        for _ in range(_MAX_TURNS):
            turn = self._chat(messages, specs)
            if not turn.tool_calls:
                final_text = turn.text
                break
            messages.append(_assistant_message(turn))

            called_stages = {
                tools_by_name[call.tool_name].stage
                for call in turn.tool_calls
                if call.tool_name in tools_by_name
            }
            for stage in [s for s in open_stages if s not in called_stages]:
                del open_stages[stage]
                yield AgentEvent("agent_status", {"agent": stage, "status": "done"})

            for call in turn.tool_calls:
                tool = tools_by_name.get(call.tool_name)
                if tool is None:
                    messages.append(
                        _tool_message(
                            call.tool_name, _error_result(f"'{call.tool_name}'은 없는 도구입니다")
                        )
                    )
                    continue
                arguments = self._resolve_arguments(tool, call, messages, specs)
                if arguments is None:
                    continue
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
                    continue
                messages.append(_tool_message(tool.spec.name, result))
                citations.extend(_collect_citations(tool, arguments, result, region))

        if not final_text:
            messages.append({"role": "user", "content": _FINAL_REQUEST})
            final_text = self._chat(messages, specs).text

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

    def _resolve_arguments(
        self,
        tool: AgentTool,
        call: LLMToolCall,
        messages: list[dict],
        specs: list[LLMToolSpec],
    ) -> dict | None:
        """스키마 위반이면 재프롬프트 1회 — 재시도도 위반이면 None(해당 호출만 스킵)."""
        violation = check_arguments(tool.spec.input_schema, call.arguments)
        if violation is None:
            return call.arguments
        messages.append(
            _tool_message(
                tool.spec.name, _error_result(f"{violation}. 올바른 인자로 다시 호출하세요")
            )
        )
        retry = self._chat(messages, specs)
        messages.append(_assistant_message(retry))
        retried = next(
            (c for c in retry.tool_calls if c.tool_name == tool.spec.name), None
        )
        if retried is None or check_arguments(tool.spec.input_schema, retried.arguments):
            return None
        return retried.arguments


def _user_message(region: str, industry: str, question: str | None) -> str:
    parts = [f"분석 지역: {region}", f"업종: {industry}"]
    if question:
        parts.append(f"사용자 질문: {question}")
    return "\n".join(parts)


def _collect_citations(tool: AgentTool, arguments: dict, result: str, region: str) -> list[dict]:
    """도구의 cite 콜백 결과를 그대로 쓰고, 콜백이 없는 도구는 fact 인용으로 대체한다."""
    if tool.cite is None:
        return [{"title": f"{tool.spec.name}: {region}", "url": "", "grade": "fact"}]
    return tool.cite(arguments, result)
