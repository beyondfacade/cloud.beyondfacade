"""sse_timeline CLI — 출력 포매터 단위 테스트 (네트워크·LLM 없음)."""

from apps.agent.adapter.inbound.cli.sse_timeline import format_line, summary_lines


def test_이벤트_종류마다_꼬리_표기가_다르다():
    assert format_line(0.04, "agent_status", {"agent": "facts", "status": "running"}).startswith(
        "+  0.04s agent_status  facts/running"
    )
    assert format_line(3.2, "report_delta", {"section": "verdict"}).endswith("verdict")
    assert format_line(1.1, "tool_call", {"agent": "funding", "tool": "search_funding"}).endswith(
        "funding/search_funding"
    )
    assert format_line(0.6, "facts", {"facts": {"a": 1}}).endswith("자")


def test_모르는_이벤트도_시각과_이름은_찍는다():
    assert format_line(12.5, "heartbeat", {}) == "+ 12.50s heartbeat"


def test_요약은_목표를_넘긴_구간을_NG로_표시한다():
    lines = summary_lines(
        {"first": 0.1, "facts": 0.5, "report_delta": 6.0}, chars=1200, deltas=42
    )

    text = "\n".join(lines)
    assert "첫 이벤트: 0.10s (목표 0.2s, OK)" in text
    assert "첫 report_delta: 6.00s (목표 4.0s, NG)" in text
    assert "report_done: — (도달 안 함)" in text
    assert "리포트: 조각 42개 · 1200자" in text
