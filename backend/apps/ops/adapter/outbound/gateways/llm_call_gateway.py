"""agent BC의 llm_call_event를 읽기 전용으로 조회한다 (cross-BC 접근은 이 구현체 안에서만)."""

from datetime import datetime

from sqlalchemy import text

from apps.ops.app.ports.output.healthcare_port import LlmCallPort
from apps.ops.domain.services.usage_series import LlmCallRecord
from core.matrix.grid_oracle_database_manager import session_scope


class LlmCallGateway(LlmCallPort):
    def records_since(self, since: datetime) -> list[LlmCallRecord]:
        with session_scope() as session:
            rows = session.execute(
                text(
                    "select occurred_at, model, outcome, latency_ms from llm_call_event "
                    "where occurred_at >= :since order by occurred_at"
                ),
                {"since": since},
            )
            return [LlmCallRecord(*row) for row in rows]
