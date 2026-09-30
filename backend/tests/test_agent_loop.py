"""analysis_interactor — 단일 에이전트 루프의 SSE 이벤트 계약 테스트 (FakeLLM, DB·네트워크 없음)."""

import json

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from apps.agent.app.use_cases.agent_tools import AgentTool
from apps.agent.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent

_FACTS = {"region": {"code": "1168064000", "name": "역삼1동"}, "verdict": {"available": False, "reason": "없다"}}

_FINAL_TEXT = (
    "[SECTION:verdict]\n### 판정\n\n🔴 위험.\n"
    "[SECTION:reasons]\n### 왜 안 되나\n\n생존 절벽이 켜졌다.\n"
    "[SECTION:analogs]\n### 유사 사례\n\n코로나 때 대면 업종이 약세였다.\n"
    "[SECTION:conditions]\n### 그래도 한다면\n\n손익분기 900만원.\n"
    "[SECTION:alternatives]\n### 대안 동네·업종\n\n제과점.\n"
    "[SECTION:funding]\n### 대안 업종 지원사업\n\n공고 2건.\n"
)

_SECTION_ORDER = ["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"]

_SIGNATURE_FIELDS = {
    "agent_status": ("agent", "status"),
    "facts": (),
    "tool_call": ("agent", "tool"),
    "report_delta": ("section",),
    "report_done": (),
}


def _signature(event: AgentEvent) -> tuple:
    """이벤트를 (type, 식별 필드…) 튜플로 축약 — 순서 계약 비교용."""
    return (event.type, *(event.payload[field] for field in _SIGNATURE_FIELDS[event.type]))


class FakeLLM(LLMGatewayPort):
    """턴 스크립트를 순서대로 뱉는 Fake — 호출 시점의 messages를 기록한다.

    `chunk`를 주면 스트림이 텍스트를 그 길이로 쪼개 흘린다(조각 단위 방출 검증용).
    """

    model_name = "fake-llm"

    def __init__(self, turns: list[LLMTurn], chunk: int | None = None) -> None:
        self._turns = list(turns)
        self._chunk = chunk
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        self.calls.append([dict(message) for message in messages])
        return self._turns.pop(0)

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]):
        turn = self.chat(messages, tools)
        for piece in _pieces(turn.text, self._chunk):
            yield LLMStreamEvent(kind="text", text=piece)
        yield LLMStreamEvent(kind="tool_calls", tool_calls=turn.tool_calls)
        yield LLMStreamEvent(kind="usage", usage=turn.usage)


def _pieces(text: str, chunk: int | None) -> list[str]:
    if not text:
        return []
    if chunk is None:
        return [text]
    return [text[index : index + chunk] for index in range(0, len(text), chunk)]


class FakeFactsCollector(ReportFactsCollector):
    """수집 결과를 고정하는 대역 — 호출 인자를 기록한다 (포트 조립 없이)."""

    def __init__(self, facts: dict | None = None) -> None:
        self.facts = _FACTS if facts is None else facts
        self.calls: list[tuple] = []

    def collect(
        self, region: str, industry: str, budget: int | None = None, question: str | None = None
    ) -> dict:
        self.calls.append((region, industry, budget, question))
        return self.facts


def _interactor(llm, tools, facts=None, **kwargs) -> AnalysisInteractor:
    return AnalysisInteractor(llm, tools, facts or FakeFactsCollector(), **kwargs)


def _final_turn(text: str = _FINAL_TEXT) -> LLMTurn:
    return LLMTurn(text=text, tool_calls=[], usage=LLMUsage(input_tokens=30, output_tokens=7))


def _market_call_turn() -> LLMTurn:
    """유효한 인자로 market 스테이지 도구를 1건 호출하는 턴."""
    return LLMTurn(
        text="",
        tool_calls=[
            LLMToolCall(
                tool_name="stub_market_tool",
                arguments={"region_code": "11680640", "industry": "cafe"},
            )
        ],
        usage=LLMUsage(input_tokens=10, output_tokens=2),
    )


def _market_tool(run=None, cite=None) -> AgentTool:
    """루프 검증용 대역 도구 — 루프는 도구가 무엇인지 모른다(주입받은 레지스트리로만 돈다)."""
    return AgentTool(
        spec=LLMToolSpec(
            name="stub_market_tool",
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
        _market_tool(cite=lambda args, result: [fact_citation, dict(fact_citation)]),
        _funding_tool(),
    ]
    llm = FakeLLM(
        [
            LLMTurn(
                text="도구를 호출한다",
                tool_calls=[
                    LLMToolCall(
                        tool_name="stub_market_tool",
                        arguments={"region_code": "11680640", "industry": "cafe"},
                    ),
                    LLMToolCall(tool_name="search_funding", arguments={"query": "카페 창업자금"}),
                ],
                usage=LLMUsage(input_tokens=100, output_tokens=20),
            ),
            _final_turn(),
        ]
    )
    interactor = _interactor(llm, tools)

    events = list(interactor.run("역삼동", "cafe", None))

    assert [_signature(event) for event in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "facts", "running"),
        ("facts",),
        ("agent_status", "facts", "done"),
        ("agent_status", "writer", "running"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "stub_market_tool"),
        ("agent_status", "funding", "running"),
        ("tool_call", "funding", "search_funding"),
        ("agent_status", "market", "done"),
        ("agent_status", "funding", "done"),
        ("report_delta", "verdict"),
        ("report_delta", "reasons"),
        ("report_delta", "analogs"),
        ("report_delta", "conditions"),
        ("report_delta", "alternatives"),
        ("report_delta", "funding"),
        ("agent_status", "writer", "done"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    assert events[11].payload["markdown"] == "### 판정\n\n🔴 위험."
    assert events[-1].payload["report_id"]
    assert events[-1].payload["citations"] == [
        {"title": "stub_market_tool: 역삼동", "url": "", "grade": "fact"},
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
    llm = FakeLLM([_market_call_turn(), _final_turn()])
    interactor = _interactor(llm, [_market_tool(cite=lambda args, result: callback_output)])

    events = list(interactor.run("역삼동", "cafe", None))

    assert events[-1].payload["citations"] == [
        {"title": "stub_market_tool: 역삼동", "url": "", "grade": "fact"},
        {"title": "한국일보", "url": "https://news.example/1", "grade": "signal"},
        {"title": "F-77", "url": "", "grade": "signal"},
    ]


def test_cite_failure_drops_citations_but_keeps_the_stream_alive():
    """cite 콜백이 예외를 던져도 도구 결과는 이력에 남고 스트림 꼬리는 끝까지 방출된다."""

    def exploding_cite(_args: dict, _result: str) -> list[dict]:
        raise ValueError("인용 형식이 예상과 다릅니다")

    llm = FakeLLM([_market_call_turn(), _final_turn()])
    interactor = _interactor(llm, [_market_tool(cite=exploding_cite)])

    events = list(interactor.run("역삼동", "cafe", None))

    assert json.loads(llm.calls[1][-1]["content"]) == {"store_count": 10}
    assert [_signature(event) for event in events[-10:]] == [
        ("agent_status", "market", "done"),
        ("report_delta", "verdict"),
        ("report_delta", "reasons"),
        ("report_delta", "analogs"),
        ("report_delta", "conditions"),
        ("report_delta", "alternatives"),
        ("report_delta", "funding"),
        ("agent_status", "writer", "done"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    assert events[-1].payload["citations"] == []


def test_missing_sections_fall_back_to_shortage_notice():
    """최종 텍스트에 없는 섹션은 폴백 문구로 채워 6건을 모두 방출한다."""
    llm = FakeLLM([_final_turn("[SECTION:verdict]\n### 판정\n\n🔴 위험.")])
    interactor = _interactor(llm, [_market_tool()])

    deltas = [event for event in interactor.run("역삼동", "cafe", None) if event.type == "report_delta"]

    assert [event.payload["section"] for event in deltas] == [
        "verdict",
        "reasons",
        "analogs",
        "conditions",
        "alternatives",
        "funding",
    ]
    assert deltas[0].payload["markdown"] == "### 판정\n\n🔴 위험."
    assert deltas[1].payload["markdown"] == "### 왜 안 되나\n\n분석 데이터가 부족합니다."
    assert deltas[5].payload["markdown"] == "### 대안 업종 지원사업\n\n분석 데이터가 부족합니다."


def test_schema_violation_reprompts_once_then_skips_and_continues():
    """필수 인자 누락 → 재프롬프트 1회, 재시도도 위반이면 해당 호출만 스킵하고 루프는 계속된다."""
    invalid_call = LLMToolCall(tool_name="stub_market_tool", arguments={"region_code": "11680640"})
    llm = FakeLLM(
        [
            LLMTurn(text="", tool_calls=[invalid_call], usage=LLMUsage(input_tokens=10, output_tokens=2)),
            LLMTurn(text="", tool_calls=[invalid_call], usage=LLMUsage(input_tokens=10, output_tokens=2)),
            _final_turn(),
        ]
    )
    interactor = _interactor(llm, [_market_tool()])

    events = list(interactor.run("역삼동", "cafe", None))

    assert len(llm.calls) == 3
    assert [message["role"] for message in llm.calls[1]] == ["system", "user", "assistant", "tool"]
    assert llm.calls[1][-1]["tool_name"] == "stub_market_tool"
    assert "industry" in llm.calls[1][-1]["content"]
    # 재시도도 위반 → 실행하지 않은 호출은 이력에 남기지 않는다 (dangling 방지)
    assert llm.calls[2] == llm.calls[1]
    assert [event for event in events if event.type == "tool_call"] == []
    assert _signature(events[0]) == ("agent_status", "orchestrator", "running")
    assert _signature(events[-1]) == ("report_done",)
    assert len([event for event in events if event.type == "report_delta"]) == 6


def test_schema_violation_retry_with_valid_arguments_runs_the_tool():
    """재프롬프트 후 올바른 인자가 오면 그 호출을 그대로 실행한다."""
    executed: list[dict] = []
    llm = FakeLLM(
        [
            LLMTurn(
                text="",
                tool_calls=[LLMToolCall(tool_name="stub_market_tool", arguments={})],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            LLMTurn(
                text="",
                tool_calls=[
                    LLMToolCall(
                        tool_name="stub_market_tool",
                        arguments={"region_code": "11680640", "industry": "cafe"},
                    )
                ],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            _final_turn(),
        ]
    )
    tool = _market_tool(run=lambda args: executed.append(args) or "{}")
    interactor = _interactor(llm, [tool])

    events = list(interactor.run("역삼동", "cafe", None))

    assert executed == [{"region_code": "11680640", "industry": "cafe"}]
    assert _signature(events[5]) == ("agent_status", "market", "running")
    assert _signature(events[6]) == ("tool_call", "market", "stub_market_tool")
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
                "name": "stub_market_tool",
                "arguments": {"region_code": "11680640", "industry": "cafe"},
            }
        }
    ]
    assert llm.calls[2][5]["tool_name"] == "stub_market_tool"


def test_valid_calls_are_answered_before_the_invalid_call_reprompt():
    """한 턴에 [위반 A, 유효 B]가 오면 B를 먼저 실행·응답한 뒤 A를 재프롬프트한다."""
    invalid = LLMToolCall(tool_name="stub_market_tool", arguments={"region_code": "11680640"})
    valid = LLMToolCall(tool_name="search_funding", arguments={"query": "카페 창업자금"})
    retried = LLMToolCall(
        tool_name="stub_market_tool",
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
    interactor = _interactor(llm, [_market_tool(), _funding_tool()])

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
    assert reprompt_messages[4]["tool_name"] == "stub_market_tool"
    assert "industry" in reprompt_messages[4]["content"]
    assert [_signature(event) for event in events[5:9]] == [
        ("agent_status", "funding", "running"),
        ("tool_call", "funding", "search_funding"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "stub_market_tool"),
    ]


def test_turn_limit_forces_a_final_report_call_and_finishes_the_contract():
    """12턴 내내 도구만 호출하면 최종 리포트를 강제 요청하는 호출 1회 뒤 계약을 완주한다."""
    tool_turn = LLMTurn(
        text="",
        tool_calls=[
            LLMToolCall(
                tool_name="stub_market_tool",
                arguments={"region_code": "11680640", "industry": "cafe"},
            )
        ],
        usage=LLMUsage(input_tokens=10, output_tokens=1),
    )
    llm = FakeLLM([tool_turn] * 12 + [_final_turn()])
    interactor = _interactor(llm, [_market_tool()])

    events = list(interactor.run("역삼동", "cafe", None))

    assert len(llm.calls) == 13
    assert llm.calls[-1][-1] == {
        "role": "user",
        "content": "도구 호출을 멈추고, 지금까지 수집한 내용만으로 최종 리포트를 6개 섹션 마커 형식에 맞춰 지금 작성하라.",
    }
    assert [_signature(event) for event in events[-10:]] == [
        ("agent_status", "market", "done"),
        ("report_delta", "verdict"),
        ("report_delta", "reasons"),
        ("report_delta", "analogs"),
        ("report_delta", "conditions"),
        ("report_delta", "alternatives"),
        ("report_delta", "funding"),
        ("agent_status", "writer", "done"),
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
                        tool_name="stub_market_tool",
                        arguments={"region_code": "99999999", "industry": "cafe"},
                    )
                ],
                usage=LLMUsage(input_tokens=10, output_tokens=2),
            ),
            _final_turn(),
        ]
    )
    interactor = _interactor(llm, [_market_tool(run=boom)])

    events = list(interactor.run("역삼동", "cafe", None))

    tool_result = llm.calls[1][-1]
    assert tool_result["role"] == "tool"
    assert json.loads(tool_result["content"]) == {"error": "행정동 코드를 찾을 수 없습니다"}
    assert [_signature(event) for event in events[5:8]] == [
        ("agent_status", "market", "running"),
        ("tool_call", "market", "stub_market_tool"),
        ("agent_status", "market", "done"),
    ]
    assert _signature(events[-1]) == ("report_done",)
    assert events[-1].payload["citations"] == []


def test_시스템_프롬프트가_다섯_섹션_마커를_순서대로_고정한다():
    """섹션 키·제목·순서는 프론트와의 계약이다 (설계서 §6 계약 표)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    markers = [
        "[SECTION:verdict] 판정",
        "[SECTION:reasons] 왜 안 되나",
        "[SECTION:conditions] 그래도 한다면",
        "[SECTION:alternatives] 대안 동네·업종",
        "[SECTION:funding] 대안 업종 지원사업",
    ]
    positions = [SYSTEM_PROMPT.find(marker) for marker in markers]

    assert all(position > 0 for position in positions), "선언되지 않은 마커가 있다"
    assert positions == sorted(positions), "마커 순서가 계약과 다르다"


def test_시스템_프롬프트가_판정을_facts_값_그대로_옮기게_한다():
    """등급을 LLM이 새로 만들면 지도 배지와 리포트가 어긋난다 (설계서 §5-2)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "`facts.verdict`" in SYSTEM_PROMPT
    assert "그대로 옮긴다" in SYSTEM_PROMPT
    assert "등급을 바꾸거나" in SYSTEM_PROMPT
    assert "🟢 추천을 쓰지 않는다" in SYSTEM_PROMPT
    assert "판정 없음" in SYSTEM_PROMPT


def test_시스템_프롬프트에_도구부터_부르라는_문장이_남아_있지_않다():
    """사실은 이미 [FACTS]로 들어간다 — 도구를 먼저 부르라는 문장은 왕복만 늘린다 (설계서 §2-4)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "가장 먼저 호출한다" not in SYSTEM_PROMPT
    assert "반드시 호출한다" not in SYSTEM_PROMPT
    assert "도구로 사실을 수집한 뒤" not in SYSTEM_PROMPT
    assert "[FACTS]" in SYSTEM_PROMPT


def test_시스템_프롬프트가_도구를_facts에_없는_것에만_쓰게_한다():
    """도구 루프는 남지만 facts가 대신할 수 있는 것을 다시 묻지 않는다 (설계서 §2-1)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    rule = SYSTEM_PROMPT[SYSTEM_PROMPT.find("⑤") : SYSTEM_PROMPT.find("[분량]")]

    assert "`[FACTS]`에 없는 것에만" in rule
    # run_finance_simulation은 13개 입력이 다 있을 때만 호출한다 (사용자 입력 없이는 못 돈다).
    finance_clause = rule[rule.find("run_finance_simulation") :]
    assert "13개 입력" in finance_clause and "주었을 때만" in finance_clause
    assert "지어내지 않는다" in rule


def test_시스템_프롬프트가_공통_충격을_업종_악재로_쓰지_못하게_한다():
    """업종 충격이 없으면 전 업종 공통 충격이 대신 실린다 — 그걸 한식 악재로 읽으면 안 된다."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    contract = SYSTEM_PROMPT[
        SYSTEM_PROMPT.find("[reasons 섹션 출력 계약]") : SYSTEM_PROMPT.find("[conditions 섹션 출력 계약]")
    ]
    assert "industry_specific" in contract
    assert "전 업종 공통 충격" in contract


def test_시스템_프롬프트가_표_대신_해석_문장을_쓰게_한다():
    """숫자는 시각 자료가 보여준다 — 글이 짧아져야 리포트가 빨라진다 (설계서 §3-5)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "[분량]" in SYSTEM_PROMPT
    assert "해석 2~4문장" in SYSTEM_PROMPT
    assert "시각 자료" in SYSTEM_PROMPT


def test_시스템_프롬프트가_수집_실패한_사실에_대처하게_한다():
    """수집이 실패한 항목은 available: false + reason으로 온다 — 그때 등급을 지어내지 않게 한다."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "available: false" in SYSTEM_PROMPT
    assert "reason" in SYSTEM_PROMPT


def test_시스템_프롬프트가_참고_신호를_경고로_쓰지_못하게_한다():
    """상권 축소는 등급에서 빠진 참고 신호다 (설계서 §7)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "advisory" in SYSTEM_PROMPT
    assert "참고" in SYSTEM_PROMPT


def test_시스템_프롬프트가_대안을_두_축_각_최대_3개로_묶는다():
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "[alternatives 섹션 출력 계약]" in SYSTEM_PROMPT
    assert "`facts.alternatives`" in SYSTEM_PROMPT
    assert "최대 3개" in SYSTEM_PROMPT
    assert "대안 없음" in SYSTEM_PROMPT


def test_시스템_프롬프트가_없는_수치를_지어내지_못하게_한다():
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "지어내지 않는다" in SYSTEM_PROMPT
    assert "caveats" in SYSTEM_PROMPT


def test_시스템_프롬프트가_지표를_벤치마크와_비교해_쓰게_한다():
    """패널에서 본 절대값을 리포트가 되풀이하지 않게 — 서울 평균·유형 중앙값 대비로 쓴다 (무대 설계서 §7)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "benchmarks" in SYSTEM_PROMPT
    assert "비교 기준 없는 절대값" in SYSTEM_PROMPT


def test_시스템_프롬프트가_conditions_절에_조건_셋을_세운다():
    """그래도 한다면 = 시간대 조건·임대료 상한·손익분기 매출. 부족액 0원 함정도 그대로 막는다."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "[conditions 섹션 출력 계약]" in SYSTEM_PROMPT
    assert "`facts.hour_gap`" in SYSTEM_PROMPT
    assert "시간대 조건" in SYSTEM_PROMPT
    assert "임대료 상한" in SYSTEM_PROMPT
    assert "손익분기 매출" in SYSTEM_PROMPT
    assert "run_finance_simulation" in SYSTEM_PROMPT
    assert "다시 계산하지 않는다" in SYSTEM_PROMPT
    assert "external_funding_need" in SYSTEM_PROMPT
    assert "\"충분합니다\"라고 쓰지 않는다" in SYSTEM_PROMPT


def test_도구_수집이_벽시계_예산을_넘기면_멈추고_리포트를_쓴다():
    """턴 수가 남아도 예산을 넘기면 수집을 멈추고 _FINAL_REQUEST로 마무리한다.

    2026-09-23 실측: 로컬 12B가 도구를 맴돌며 12턴을 다 쓰면 534.7초·558.4초가 걸렸고 리포트는
    비어 있었다. 턴 수만으로는 소요 시간이 안 잡힌다.
    """
    from apps.agent.app.use_cases.analysis_interactor import _TOOL_LOOP_BUDGET_SECONDS

    # ① deadline 계산 ② 1회차 검사(통과) ③ 2회차 검사(초과)
    clock = iter([0.0, 0.0, _TOOL_LOOP_BUDGET_SECONDS + 1.0])
    llm = FakeLLM([_market_call_turn(), _final_turn()])
    interactor = _interactor(llm, [_market_tool()], now=lambda: next(clock))

    events = list(interactor.run("11680640", "cafe", None))

    # 도구 턴 1회만 돌고 예산 초과로 빠져나와, 마무리 턴이 리포트를 만든다
    assert len(llm.calls) == 2
    assert llm.calls[-1][-1]["content"].startswith("도구 호출을 멈추고")
    assert [e.payload["section"] for e in events if e.type == "report_delta"] == [
        "verdict",
        "reasons",
        "analogs",
        "conditions",
        "alternatives",
        "funding",
    ]


def test_예산_안에서는_턴_한도까지_정상_수집한다():
    """빠른 응답(시계가 안 흐름)에서는 기존 동작 그대로 — 예산이 조기 종료를 만들지 않는다."""
    llm = FakeLLM([_market_call_turn(), _final_turn()])
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("11680640", "cafe", None))

    assert len(llm.calls) == 2  # 도구 턴 + 최종 텍스트 턴
    assert any(e.type == "tool_call" for e in events)
    assert [e.payload["section"] for e in events if e.type == "report_delta"][0] == "verdict"


class _BoomLLM(LLMGatewayPort):
    """n번째 호출부터 터지는 Fake — LLM 장애·타임아웃 재현."""

    model_name = "boom-llm"

    def __init__(self, turns: list[LLMTurn], fail_from: int) -> None:
        self._turns = list(turns)
        self._fail_from = fail_from
        self.calls = 0

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        self.calls += 1
        if self.calls >= self._fail_from:
            raise TimeoutError("ollama read timeout")
        return self._turns.pop(0)

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]):
        turn = self.chat(messages, tools)
        if turn.text:
            yield LLMStreamEvent(kind="text", text=turn.text)
        yield LLMStreamEvent(kind="tool_calls", tool_calls=turn.tool_calls)
        yield LLMStreamEvent(kind="usage", usage=turn.usage)


def test_수집_턴이_터져도_리포트는_나간다():
    """LLM 타임아웃이 스트림을 끊으면 화면에 리포트가 아예 안 뜬다(NO_ARTICLE). 마무리로 넘어간다."""
    llm = _BoomLLM([_market_call_turn(), _final_turn()], fail_from=2)
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("11680640", "cafe", None))

    assert [e.payload["section"] for e in events if e.type == "report_delta"] == [
        "verdict",
        "reasons",
        "analogs",
        "conditions",
        "alternatives",
        "funding",
    ]
    assert events[-1].type == "report_done"


def test_마무리_턴까지_터지면_폴백_섹션으로_낸다():
    """빈 스트림보다 '분석 데이터가 부족합니다'가 낫다 — 화면이 끝을 알 수 있어야 한다.

    판정·대안은 facts가 있으므로 코드가 쓴다 — LLM이 전부 죽어도 판정은 화면에 나간다.
    """
    llm = _BoomLLM([], fail_from=1)
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("11680640", "cafe", None))

    deltas = {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}
    assert len(deltas) == 6
    assert "판정 없음" in deltas["verdict"]
    assert all(
        "분석 데이터가 부족합니다" in deltas[name]
        for name in ("reasons", "analogs", "conditions", "funding")
    )
    assert events[-1].type == "report_done"


def test_시스템_프롬프트가_공고_후보를_자격_확정으로_쓰지_못하게_한다():
    """후보는 해당 가능성이지 자격 판정이 아니다 (설계서 §6). 대안 업종 공고를 먼저 놓는다."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "[funding 섹션 출력 계약]" in SYSTEM_PROMPT
    assert "`facts.funding_candidates`" in SYSTEM_PROMPT
    assert "자격 확정이 아니라" in SYSTEM_PROMPT
    assert "대안 업종" in SYSTEM_PROMPT


# --- facts 선수집 (설계서 §3-3) ---


def test_facts는_LLM을_부르기_전에_먼저_나간다():
    """프론트는 이 프레임만으로 시각 자료를 다 그린다 — 글보다 먼저 화면이 차야 한다."""
    collector = FakeFactsCollector()
    llm = FakeLLM([_final_turn()])
    interactor = _interactor(llm, [_market_tool()], facts=collector, budget=50_000_000)

    events = list(interactor.run("1168064000", "korean_food", "바이러스가 돌면?"))

    assert [_signature(event) for event in events[:4]] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "facts", "running"),
        ("facts",),
        ("agent_status", "facts", "done"),
    ]
    assert events[2].payload == {"facts": collector.facts}  # 프론트 계약은 중첩이다
    # 질문은 유사 사례의 유형 단서라 사실 수집에도 넘긴다
    assert collector.calls == [("1168064000", "korean_food", 50_000_000, "바이러스가 돌면?")]


def test_수집한_사실이_LLM_첫_메시지에_통째로_실린다():
    """도구를 맴돌며 턴을 쌓지 않게 — 사실은 한 번에 들어간다 (설계서 §3-3②)."""
    llm = FakeLLM([_final_turn()])
    interactor = _interactor(llm, [_market_tool()])

    list(interactor.run("1168064000", "korean_food", "괜찮을까요?"))

    user_message = llm.calls[0][1]["content"]
    assert user_message.startswith("분석 지역: 1168064000")
    assert "사용자 질문: 괜찮을까요?" in user_message
    assert json.loads(user_message.split("[FACTS]\n")[1]) == _FACTS  # 프롬프트에는 사실만


def test_LLM이_판정_대안을_빼먹으면_코드가_facts로_채운다():
    """판정은 규칙이 내린다 — LLM이 안 써도 판정·대안은 화면에 나간다 (설계서 §2-4)."""
    facts = FakeFactsCollector(
        {
            "verdict": {
                "available": True,
                "verdict_code": "red",
                "on_count": 1,
                "strong_count": 1,
                "signals": [
                    {"key": "survival_cliff", "level": "strong", "evidence": "3년 생존율 41%입니다.", "advisory": False}
                ],
                "computed_at": "2026-09-29T03:00:00",
            },
            "alternatives": {
                "available": True,
                "industries": [{"industry_name": "제과점", "verdict_code": "clear"}],
                "regions": [],
            },
        }
    )
    llm = FakeLLM([_final_turn("[SECTION:reasons]\n### 왜 안 되나\n\n생존 절벽이 켜졌다.")])
    interactor = _interactor(llm, [_market_tool()], facts=facts)

    deltas = {
        event.payload["section"]: event.payload["markdown"]
        for event in interactor.run("1168064000", "korean_food", None)
        if event.type == "report_delta"
    }

    assert "비추천" in deltas["verdict"]
    assert "3년 생존율 41%입니다." in deltas["verdict"]
    assert "제과점" in deltas["alternatives"]
    assert "대안 없음" in deltas["alternatives"]  # 빈 축
    assert deltas["conditions"] == "### 그래도 한다면\n\n분석 데이터가 부족합니다."


def test_LLM이_쓴_판정_섹션은_폴백이_덮어쓰지_않는다():
    """글은 LLM이 쓴다 — 코드는 빈자리만 메운다."""
    llm = FakeLLM([_final_turn()])
    interactor = _interactor(llm, [_market_tool()])

    deltas = {
        event.payload["section"]: event.payload["markdown"]
        for event in interactor.run("1168064000", "korean_food", None)
        if event.type == "report_delta"
    }

    assert deltas["verdict"] == "### 판정\n\n🔴 위험."


# --- 토큰 스트리밍 (설계서 §3-3③) ---


def test_본문은_조각_단위로_흘러나온다():
    """같은 섹션의 report_delta가 여러 번 온다 — 프론트는 append한다 (설계서 §3-2)."""
    from apps.agent.domain.services.section_stream import concat_sections

    llm = FakeLLM([_final_turn()], chunk=13)
    interactor = _interactor(llm, [_market_tool()])

    deltas = [e for e in interactor.run("1168064000", "korean_food", None) if e.type == "report_delta"]

    sections = [e.payload["section"] for e in deltas]
    assert len(deltas) > 5, "조각이 아니라 섹션 통째로 나갔다"
    assert sections.count("verdict") > 1
    assert sections == sorted(sections, key=_SECTION_ORDER.index)
    assert concat_sections((e.payload["section"], e.payload["markdown"]) for e in deltas) == (
        "### 판정\n\n🔴 위험.\n\n"
        "### 왜 안 되나\n\n생존 절벽이 켜졌다.\n\n"
        "### 유사 사례\n코로나 때 대면 업종이 약세였다.\n\n"  # 한 문단 섹션 — 빈 줄은 줄바꿈 하나로
        "### 그래도 한다면\n\n손익분기 900만원.\n\n"
        "### 대안 동네·업종\n\n제과점.\n\n"
        "### 대안 업종 지원사업\n\n공고 2건."
    )


def test_첫_마커_앞_서문은_리포트에_실리지_않는다():
    """도구 호출 전 잡담은 본문이 아니다 — 서문이 판정 절 머리에 붙으면 카드와 글이 어긋난다."""
    llm = FakeLLM([_final_turn("알겠습니다. 이제 작성합니다.\n" + _FINAL_TEXT)], chunk=7)
    interactor = _interactor(llm, [_market_tool()])

    deltas = [e for e in interactor.run("1168064000", "korean_food", None) if e.type == "report_delta"]

    first = [e for e in deltas if e.payload["section"] == "verdict"][0]
    assert first.payload["markdown"].startswith("### 판정")
    assert all("알겠습니다" not in e.payload["markdown"] for e in deltas)


class _MidStreamBoomLLM(LLMGatewayPort):
    """텍스트를 얼마간 흘린 뒤 끊기는 Fake — 스트림 중단 재현."""

    model_name = "mid-boom"

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def chat(self, messages, tools) -> LLMTurn:
        raise AssertionError("스트림 중단 뒤에는 다시 부르지 않는다")

    def stream(self, messages, tools):
        self.calls += 1
        yield LLMStreamEvent(kind="text", text=self._text)
        raise TimeoutError("연결이 끊겼습니다")


def test_스트림이_끊겨도_흘린_글은_남고_나머지는_폴백으로_채운다():
    """반쯤 쓴 글을 버리지 않는다 — 남은 섹션만 폴백이 메우고 스트림은 정상 종료한다 (설계서 §3-4)."""
    llm = _MidStreamBoomLLM("[SECTION:verdict]\n### 판정\n\n🔴 위험.\n[SECTION:reasons]\n생존 절벽.")
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("1168064000", "korean_food", None))

    deltas = {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}
    assert llm.calls == 1  # 끊긴 뒤 같은 글을 다시 쓰게 하지 않는다
    assert deltas["verdict"] == "### 판정\n\n🔴 위험."
    assert deltas["reasons"] == "생존 절벽."
    assert "분석 데이터가 부족합니다" in deltas["conditions"]
    assert set(deltas) == {"verdict", "reasons", "analogs", "conditions", "alternatives", "funding"}
    assert _signature(events[-1]) == ("report_done",)


def test_writer_스테이지가_생성_전후로_열리고_닫힌다():
    """프론트 진행 패널이 '글 쓰는 중'을 보여주는 근거다 (설계서 §3-2)."""
    llm = FakeLLM([_final_turn()])
    interactor = _interactor(llm, [_market_tool()])

    events = list(interactor.run("1168064000", "korean_food", None))

    writer = [i for i, e in enumerate(events) if _signature(e)[:2] == ("agent_status", "writer")]
    first_delta = next(i for i, e in enumerate(events) if e.type == "report_delta")
    assert [events[i].payload["status"] for i in writer] == ["running", "done"]
    assert writer[0] < first_delta < writer[1]


def test_시스템_프롬프트가_판정_글을_배지_한_줄_해석으로_묶는다():
    """배지·신호 목록·산출일은 판정 카드가 그린다 — 글이 그걸 되풀이하면 화면이 두 번 같은 말을 한다."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    contract = SYSTEM_PROMPT[
        SYSTEM_PROMPT.find("[verdict 섹션 출력 계약]") : SYSTEM_PROMPT.find("[reasons 섹션 출력 계약]")
    ]
    assert "배지 한 줄 해석" in contract
    assert "산출일" not in contract  # 카드가 이미 적는다
    assert "`evidence` 문장을 그대로 옮긴다" not in contract


def test_시스템_프롬프트가_섹션을_쓰기_시작하면_도구를_금지한다():
    """마커 뒤 도구 호출이 오면 이미 흘려보낸 조각을 되돌릴 수 없다 (설계서 §9)."""
    from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT

    assert "섹션을 쓰기 시작하면 도구를 부르지 않는다" in SYSTEM_PROMPT


def test_빈_턴이_와도_마무리_요청으로_다시_쓰게_한다():
    """글도 도구 호출도 없는 턴은 예외가 안 난다(생각하다 MAX_TOKENS·세이프티 차단).

    여기서 끝내 버리면 다섯 절이 모두 '분석 데이터가 부족합니다'로 나간다.
    """
    empty = LLMTurn(text="", tool_calls=[], usage=LLMUsage(input_tokens=5, output_tokens=0))
    llm = FakeLLM([empty, _final_turn()])
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("1168064000", "korean_food", None))

    assert len(llm.calls) == 2, "빈 턴 뒤 마무리 스트림을 돌리지 않았다"
    assert llm.calls[1][-1]["content"].startswith("도구 호출을 멈추고")
    deltas = {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}
    assert deltas["verdict"] == "### 판정\n\n🔴 위험."
    assert all("분석 데이터가 부족합니다" not in md for md in deltas.values())


def test_마커_없는_글만_온_턴도_마무리_요청으로_다시_쓰게_한다():
    """마커가 하나도 없으면 리포트를 쓴 게 아니다 — 서문은 버려지므로 다섯 절이 전부 폴백이 된다.

    마커 없는 글은 이력에 쌓이지 않으니(조각이 버려진다) 다시 써도 같은 글이 겹치지 않는다.
    """
    llm = FakeLLM([_final_turn("마커 없이 그냥 쓴 리포트입니다."), _final_turn()])
    interactor = _interactor(llm, [_market_tool()], now=lambda: 0.0)

    events = list(interactor.run("1168064000", "korean_food", None))

    assert len(llm.calls) == 2, "마커 없는 턴 뒤 마무리 스트림을 돌리지 않았다"
    assert llm.calls[1][-1]["content"].startswith("도구 호출을 멈추고")
    deltas = {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}
    assert deltas["verdict"] == "### 판정\n\n🔴 위험."
    assert all("분석 데이터가 부족합니다" not in md for md in deltas.values())
