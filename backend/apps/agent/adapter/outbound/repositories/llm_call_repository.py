from apps.agent.adapter.outbound.orms.llm_call_event_orm import LlmCallEventOrm
from apps.agent.app.ports.output.llm_call_port import LlmCallRecorderPort
from apps.agent.domain.entities.llm_call_entity import LlmCall
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyLlmCallRecorder(LlmCallRecorderPort):
    def record(self, call: LlmCall) -> None:
        with session_scope() as session:
            session.add(
                LlmCallEventOrm(
                    occurred_at=call.occurred_at,
                    model=call.model[:128],
                    outcome=call.outcome.value,
                    error_kind=call.error_kind[:128] if call.error_kind else None,
                    latency_ms=call.latency_ms,
                )
            )
