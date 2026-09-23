"""에이전트 평가 자동 채점 단위 테스트."""

from apps.agent.adapter.inbound.cli.agent_eval_scoring import (
    check_rule_keywords,
    score_tool_calls,
    section_completion,
)
from apps.agent.domain.entities.agent_event_entity import AgentEvent


def test_score_tool_calls_counts_calls_and_skips():
    events = [
        AgentEvent("tool_call", {"agent": "market", "tool": "a", "summary": "ok"}),
        AgentEvent("tool_call", {"agent": "market", "tool": "b", "summary": "스키마 위반 스킵"}),
        AgentEvent("agent_status", {"agent": "market", "status": "done"}),
    ]
    assert score_tool_calls(events) == {"calls": 2, "skipped": 1}


def test_check_rule_keywords_detects_bank_recommend_and_slur():
    md = "국민은행에서 대출 받으세요. 외국인 많아 위험합니다."
    hits = check_rule_keywords(md)
    assert any(h.startswith("bank_recommend:") for h in hits)
    assert any(h.startswith("foreigner_slur:") for h in hits)


def test_check_rule_keywords_clean_report_returns_empty():
    assert check_rule_keywords("역삼1동 카페는 경쟁이 있으나 수요가 뒷받침됩니다.") == []


def test_section_completion_counts_non_placeholder():
    events = [
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 종합\n\n양호"}),
        AgentEvent(
            "report_delta",
            {"section": "market", "markdown": "### 상권\n\n분석 데이터가 부족합니다."},
        ),
    ]
    result = section_completion(events)
    assert result["complete"] == 1
    assert result["total"] == 5
