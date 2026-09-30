"""AgentEvent 엔티티 — 프론트 SSE 계약(shared/api/types.ts)의 미러 (stdlib만 import)."""

from dataclasses import dataclass


@dataclass
class AgentEvent:
    """스트리밍 이벤트 1건.

    type별 payload 필드:
    - agent_status : {agent, status}        agent ∈ orchestrator|facts|writer|market|shock|funding, status ∈ running|done
    - facts        : ReportFacts dict 13키    LLM 호출 전 코드가 모은 사실 (설계서 §3-1)
    - tool_call    : {agent, tool, summary}
    - report_delta : {section, markdown}    section ∈ verdict|reasons|conditions|alternatives|funding
                                            **조각 단위**다 — 같은 section이 여러 번 온다(프론트는 append)
    - report_done  : {report_id, citations}
    """

    type: str
    payload: dict
