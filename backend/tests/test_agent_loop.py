"""analysis_interactor — 단일 에이전트 루프의 SSE 이벤트 계약 테스트 (FakeLLM, DB·네트워크 없음)."""

import json

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from apps.agent.app.use_cases.agent_tools import AgentTool
from apps.agent.app.use_cases.analysis_interactor import (
    AnalysisInteractor,
    split_report_sections,
)
from apps.agent.domain.entities.agent_event_entity import AgentEvent

_FINAL_TEXT = (
    "[SECTION:verdict]\n### 종합 판정\n\n조건부 추천.\n"
    "[SECTION:market]\n### 상권 기초체력\n\n점포수 10개.\n"
    "[SECTION:shock]\n### 충격 취약도\n\nV자 회복.\n"
    "[SECTION:funding]\n### 자금 조달\n\n공고 2건.\n"
    "[SECTION:calculator]\n### 비용 계산\n\n손익분기 1.2년.\n"
)

_SIGNATURE_FIELDS = {
    "agent_status": ("agent", "status"),
    "tool_call": ("agent", "tool"),
    "report_delta": ("section",),
    "report_done": (),
}


def _signature(event: AgentEvent) -> tuple:
    """이벤트를 (type, 식별 필드…) 튜플로 축약 — 순서 계약 비교용."""
    return (event.type, *(event.payload[field] for field in _SIGNATURE_FIELDS[event.type]))


class FakeLLM(LLMGatewayPort):
    """턴 스크립트를 순서대로 뱉는 Fake — 호출 시점의 messages를 기록한다."""

    model_name = "fake-llm"

    def __init__(self, turns: list[LLMTurn]) -> None:
        self._turns = list(turns)
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        self.calls.append([dict(message) for message in messages])
        return self._turns.pop(0)


def _final_turn(text: str = _FINAL_TEXT) -> LLMTurn:
    return LLMTurn(text=text, tool_calls=[], usage=LLMUsage(input_tokens=30, output_tokens=7))


def _metrics_tool(run=None, cite=None) -> AgentTool:
    return AgentTool(
        spec=LLMToolSpec(
            name="get_region_metrics",
            description="지표 조회",
            input_schema={
                "type": "object",
                "properties": {
                    "region_code": {"type": "string"},
                    "industry": {"type": "string"},
                },
                "required": ["region_code", "industry"],
            },
        ),
        stage="market",
        run=run or (lambda args: json.dumps({"store_count": 10}, ensure_ascii=False)),
        cite=cite,
    )


def _funding_tool() -> AgentTool:
    return AgentTool(
        spec=LLMToolSpec(
            name="search_funding",
            description="공고 검색",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        stage="funding",
        run=lambda args: json.dumps([], ensure_ascii=False),
        cite=None,
    )


def test_event_order_contract_for_two_stage_tool_turn():
    """1턴 도구 2개(market·funding) → 2턴 최종 텍스트: 이벤트 순서 계약 전체."""
    duplicated_citation = {"title": "지표", "url": "https://example.com/m", "grade": "fact"}
    tools = [
        _metrics_tool(cite=lambda args, result: [duplicated_citation, dict(duplicated_citation)]),
        _funding_tool(),
    ]
    llm = FakeLLM(
        [
            LLMTurn(
                text="도구를 호출한다",
                tool_calls=[
                    LLMToolCall(
                        tool_name="get_region_metrics",
                        arguments={"region_code": "11680640", "industry": "cafe"},
                    ),
                    LLMToolCall(tool_name="search_funding", arguments={"query": "카페 창업자금"}),
                ],
                usage=LLMUsage(input_tokens=100, output_tokens=20),
            ),
            _final_turn(),
        ]
    )
    interactor = AnalysisInteractor(llm, tools)

    events = list(interactor.run("역삼동", "cafe", None))

    assert [_signature(event) for event in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "get_region_metrics"),
        ("agent_status", "funding", "running"),
        ("tool_call", "funding", "search_funding"),
        ("agent_status", "market", "done"),
        ("agent_status", "funding", "done"),
        ("report_delta", "verdict"),
        ("report_delta", "market"),
        ("report_delta", "shock"),
        ("report_delta", "funding"),
        ("report_delta", "calculator"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    assert events[7].payload["markdown"] == "### 종합 판정\n\n조건부 추천."
    assert events[-1].payload["report_id"]
    assert events[-1].payload["citations"] == [
        duplicated_citation,
        {"title": "search_funding: 역삼동", "url": "", "grade": "fact"},
    ]
    assert interactor.last_usage == LLMUsage(input_tokens=130, output_tokens=27)


def test_split_report_sections_parses_five_markers():
    """섹션 파서 정상 — 마커 5개를 순서대로 분할한다."""
    sections = split_report_sections(_FINAL_TEXT)

    assert list(sections) == ["verdict", "market", "shock", "funding", "calculator"]
    assert sections["calculator"] == "### 비용 계산\n\n손익분기 1.2년."


def test_missing_sections_fall_back_to_shortage_notice():
    """최종 텍스트에 없는 섹션은 폴백 문구로 채워 5건을 모두 방출한다."""
    llm = FakeLLM([_final_turn("[SECTION:verdict]\n### 종합 판정\n\n추천.")])
    interactor = AnalysisInteractor(llm, [_metrics_tool()])

    deltas = [event for event in interactor.run("역삼동", "cafe", None) if event.type == "report_delta"]

    assert [event.payload["section"] for event in deltas] == [
        "verdict",
        "market",
        "shock",
        "funding",
        "calculator",
    ]
    assert deltas[0].payload["markdown"] == "### 종합 판정\n\n추천."
    assert deltas[1].payload["markdown"] == "### 상권 기초체력\n\n분석 데이터가 부족합니다."
    assert deltas[4].payload["markdown"] == "### 비용 계산\n\n분석 데이터가 부족합니다."


def test_split_report_sections_keeps_last_duplicate_marker():
    """같은 마커가 두 번 나오면 뒤에 나온 본문이 이긴다."""
    sections = split_report_sections(
        "[SECTION:verdict]\n초안\n[SECTION:verdict]\n최종본"
    )

    assert sections["verdict"] == "최종본"


def test_schema_violation_reprompts_once_then_skips_and_continues():
    """필수 인자 누락 → 재프롬프트 1회, 재시도도 위반이면 해당 호출만 스킵하고 루프는 계속된다."""
    invalid_call = LLMToolCall(tool_name="get_region_metrics", arguments={"region_code": "11680640"})
    llm = FakeLLM(
        [
            LLMTurn(text="", tool_calls=[invalid_call], usage=LLMUsage(input_tokens=10, output_tokens=2)),
            LLMTurn(text="", tool_calls=[invalid_call], usage=LLMUsage(input_tokens=10, output_tokens=2)),
            _final_turn(),
        ]
    )
    interactor = AnalysisInteractor(llm, [_metrics_tool()])

    events = list(interactor.run("역삼동", "cafe", None))

    assert len(llm.calls) == 3
    assert "industry" in llm.calls[1][-1]["content"]
    assert llm.calls[1][-1]["role"] == "tool"
    assert [event for event in events if event.type == "tool_call"] == []
    assert _signature(events[0]) == ("agent_status", "orchestrator", "running")
    assert _signature(events[-1]) == ("report_done",)
    assert len([event for event in events if event.type == "report_delta"]) == 5


def test_schema_violation_retry_with_valid_arguments_runs_the_tool():
    """재프롬프트 후 올바른 인자가 오면 그 호출을 그대로 실행한다."""
    executed: list[dict] = []
    llm = FakeLLM(
        [
            LLMTurn(
                text="",
                tool_calls=[LLMToolCall(tool_name="get_region_metrics", arguments={})],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            LLMTurn(
                text="",
                tool_calls=[
                    LLMToolCall(
                        tool_name="get_region_metrics",
                        arguments={"region_code": "11680640", "industry": "cafe"},
                    )
                ],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            _final_turn(),
        ]
    )
    tool = _metrics_tool(run=lambda args: executed.append(args) or "{}")
    interactor = AnalysisInteractor(llm, [tool])

    events = list(interactor.run("역삼동", "cafe", None))

    assert executed == [{"region_code": "11680640", "industry": "cafe"}]
    assert _signature(events[1]) == ("agent_status", "market", "running")
    assert _signature(events[2]) == ("tool_call", "market", "get_region_metrics")


def test_turn_limit_forces_a_final_report_call_and_finishes_the_contract():
    """12턴 내내 도구만 호출하면 최종 리포트를 강제 요청하는 호출 1회 뒤 계약을 완주한다."""
    tool_turn = LLMTurn(
        text="",
        tool_calls=[
            LLMToolCall(
                tool_name="get_region_metrics",
                arguments={"region_code": "11680640", "industry": "cafe"},
            )
        ],
        usage=LLMUsage(input_tokens=10, output_tokens=1),
    )
    llm = FakeLLM([tool_turn] * 12 + [_final_turn()])
    interactor = AnalysisInteractor(llm, [_metrics_tool()])

    events = list(interactor.run("역삼동", "cafe", None))

    assert len(llm.calls) == 13
    assert llm.calls[-1][-1] == {
        "role": "user",
        "content": "도구 호출을 멈추고, 지금까지 수집한 내용만으로 최종 리포트를 5개 섹션 마커 형식에 맞춰 지금 작성하라.",
    }
    assert [_signature(event) for event in events[-8:]] == [
        ("agent_status", "market", "done"),
        ("report_delta", "verdict"),
        ("report_delta", "market"),
        ("report_delta", "shock"),
        ("report_delta", "funding"),
        ("report_delta", "calculator"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    assert interactor.last_usage == LLMUsage(input_tokens=150, output_tokens=19)


def test_tool_run_exception_is_fed_back_as_error_and_loop_continues():
    """도구 run이 예외를 던져도 루프는 죽지 않고 오류를 결과로 되먹인 뒤 계약을 완주한다."""

    def boom(_args: dict) -> str:
        raise RuntimeError("행정동 코드를 찾을 수 없습니다")

    llm = FakeLLM(
        [
            LLMTurn(
                text="",
                tool_calls=[
                    LLMToolCall(
                        tool_name="get_region_metrics",
                        arguments={"region_code": "99999999", "industry": "cafe"},
                    )
                ],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            _final_turn(),
        ]
    )
    interactor = AnalysisInteractor(llm, [_metrics_tool(run=boom)])

    events = list(interactor.run("역삼동", "cafe", None))

    tool_result = llm.calls[1][-1]
    assert tool_result["role"] == "tool"
    assert json.loads(tool_result["content"]) == {"error": "행정동 코드를 찾을 수 없습니다"}
    assert [_signature(event) for event in events[:4]] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "get_region_metrics"),
        ("agent_status", "market", "done"),
    ]
    assert _signature(events[-1]) == ("report_done",)
    assert events[-1].payload["citations"] == []
