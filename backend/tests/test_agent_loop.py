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


def _metrics_call_turn() -> LLMTurn:
    """유효한 인자로 get_region_metrics를 1건 호출하는 턴."""
    return LLMTurn(
        text="",
        tool_calls=[
            LLMToolCall(
                tool_name="get_region_metrics",
                arguments={"region_code": "11680640", "industry": "cafe"},
            )
        ],
        usage=LLMUsage(input_tokens=10, output_tokens=2),
    )


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
    fact_citation = {
        "grade": "fact",
        "source": "region_industry_metric",
        "region_code": "11680640",
        "industry": "cafe",
    }
    tools = [
        _metrics_tool(cite=lambda args, result: [fact_citation, dict(fact_citation)]),
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
        {"title": "get_region_metrics: 역삼동", "url": "", "grade": "fact"},
        {"title": "search_funding: 역삼동", "url": "", "grade": "fact"},
    ]
    assert interactor.last_usage == LLMUsage(input_tokens=130, output_tokens=27)


def test_callback_citations_are_normalized_to_title_url_grade():
    """cite 콜백의 실제 출력 형태를 프론트 계약 {title, url, grade} 3키로 정규화한다."""
    callback_output = [
        {
            "grade": "fact",
            "source": "region_industry_metric",
            "region_code": "11680640",
            "industry": "cafe",
        },
        {
            "grade": "signal",
            "source_type": "news",
            "source_id": "news-1",
            "url": "https://news.example/1",
            "org": "한국일보",
        },
        {
            "grade": "signal",
            "source_type": "funding",
            "source_id": "F-77",
            "url": None,
            "org": None,
        },
    ]
    llm = FakeLLM([_metrics_call_turn(), _final_turn()])
    interactor = AnalysisInteractor(llm, [_metrics_tool(cite=lambda args, result: callback_output)])

    events = list(interactor.run("역삼동", "cafe", None))

    assert events[-1].payload["citations"] == [
        {"title": "get_region_metrics: 역삼동", "url": "", "grade": "fact"},
        {"title": "한국일보", "url": "https://news.example/1", "grade": "signal"},
        {"title": "F-77", "url": "", "grade": "signal"},
    ]


def test_cite_failure_drops_citations_but_keeps_the_stream_alive():
    """cite 콜백이 예외를 던져도 도구 결과는 이력에 남고 스트림 꼬리는 끝까지 방출된다."""

    def exploding_cite(_args: dict, _result: str) -> list[dict]:
        raise ValueError("인용 형식이 예상과 다릅니다")

    llm = FakeLLM([_metrics_call_turn(), _final_turn()])
    interactor = AnalysisInteractor(llm, [_metrics_tool(cite=exploding_cite)])

    events = list(interactor.run("역삼동", "cafe", None))

    assert json.loads(llm.calls[1][-1]["content"]) == {"store_count": 10}
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
    assert events[-1].payload["citations"] == []


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
    assert [message["role"] for message in llm.calls[1]] == ["system", "user", "assistant", "tool"]
    assert llm.calls[1][-1]["tool_name"] == "get_region_metrics"
    assert "industry" in llm.calls[1][-1]["content"]
    # 재시도도 위반 → 실행하지 않은 호출은 이력에 남기지 않는다 (dangling 방지)
    assert llm.calls[2] == llm.calls[1]
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
    # 이력: assistant(위반 호출) → tool(위반 통보) → assistant(재시도 호출 1건) → tool(결과)
    assert [message["role"] for message in llm.calls[2]] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert llm.calls[2][4]["tool_calls"] == [
        {
            "function": {
                "name": "get_region_metrics",
                "arguments": {"region_code": "11680640", "industry": "cafe"},
            }
        }
    ]
    assert llm.calls[2][5]["tool_name"] == "get_region_metrics"


def test_valid_calls_are_answered_before_the_invalid_call_reprompt():
    """한 턴에 [위반 A, 유효 B]가 오면 B를 먼저 실행·응답한 뒤 A를 재프롬프트한다."""
    invalid = LLMToolCall(tool_name="get_region_metrics", arguments={"region_code": "11680640"})
    valid = LLMToolCall(tool_name="search_funding", arguments={"query": "카페 창업자금"})
    retried = LLMToolCall(
        tool_name="get_region_metrics",
        arguments={"region_code": "11680640", "industry": "cafe"},
    )
    llm = FakeLLM(
        [
            LLMTurn(
                text="",
                tool_calls=[invalid, valid],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            LLMTurn(
                text="다시 호출한다",
                tool_calls=[retried],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            _final_turn(),
        ]
    )
    interactor = AnalysisInteractor(llm, [_metrics_tool(), _funding_tool()])

    events = list(interactor.run("역삼동", "cafe", None))

    reprompt_messages = llm.calls[1]
    assert [message["role"] for message in reprompt_messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "tool",
    ]
    assert reprompt_messages[3]["tool_name"] == "search_funding"  # 유효 호출 응답이 먼저
    assert reprompt_messages[4]["tool_name"] == "get_region_metrics"
    assert "industry" in reprompt_messages[4]["content"]
    assert [_signature(event) for event in events[:5]] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "funding", "running"),
        ("tool_call", "funding", "search_funding"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "get_region_metrics"),
    ]


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


def test_시스템_프롬프트가_market_슬롯_여섯을_순서대로_고정한다():
    """market 섹션은 자유 서술이 아니다 — 라벨 6종이 선언된 순서 그대로 있어야 한다 (설계서 §7-4)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    labels = ["한 줄 요약", "동네 설명", "고객 구성", "시간대 특성", "주의점", "확인할 것"]
    positions = [SYSTEM_PROMPT.find(f"**{label}**") for label in labels]

    assert all(position > 0 for position in positions), "선언되지 않은 슬롯이 있다"
    assert positions == sorted(positions), "슬롯 순서가 계약과 다르다"


def test_시스템_프롬프트가_없는_수치를_지어내지_못하게_한다():
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "지어내지 않는다" in SYSTEM_PROMPT
    assert "caveats" in SYSTEM_PROMPT


def test_시스템_프롬프트가_동네_설명과_주의점을_벤치마크와_비교해_쓰게_한다():
    """패널에서 본 절대값을 리포트가 되풀이하지 않게 — 서울 평균·유형 중앙값 대비로 쓴다 (무대 설계서 §7)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "benchmarks" in SYSTEM_PROMPT
    assert "비교 기준 없는 절대값" in SYSTEM_PROMPT
