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
    """기대 섹션은 재편된 5개 키다 — alternatives도 완성으로 세어야 한다 (설계서 §6)."""
    events = [
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n\n🔴 위험"}),
        AgentEvent(
            "report_delta",
            {"section": "reasons", "markdown": "### 왜 안 되나\n\n분석 데이터가 부족합니다."},
        ),
        AgentEvent(
            "report_delta",
            {"section": "alternatives", "markdown": "### 대안 동네·업종\n\n제과점"},
        ),
    ]
    result = section_completion(events)
    assert result["complete"] == 2
    assert result["total"] == 5


def test_section_completion은_조각_delta를_이어_붙인다():
    """delta가 조각 단위가 되면 마지막 조각만 보고 판단하던 채점이 어긋난다 (설계서 §3-2)."""
    events = [
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n\n"}),
        AgentEvent("report_delta", {"section": "verdict", "markdown": "🔴 위험"}),
    ]

    result = section_completion(events)

    assert result["complete"] == 1
