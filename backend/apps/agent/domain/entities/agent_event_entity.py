"""AgentEvent 엔티티 — 프론트 SSE 계약(shared/api/types.ts)의 미러 (stdlib만 import)."""

from dataclasses import dataclass


@dataclass
class AgentEvent:
    """스트리밍 이벤트 1건.

    type별 payload 필드:
    - agent_status : {agent, status}        agent ∈ orchestrator|market|shock|funding, status ∈ running|done
    - tool_call    : {agent, tool, summary}
    - report_delta : {section, markdown}    section ∈ verdict|market|shock|funding|calculator
    - report_done  : {report_id, citations}
    """

    type: str
    payload: dict
