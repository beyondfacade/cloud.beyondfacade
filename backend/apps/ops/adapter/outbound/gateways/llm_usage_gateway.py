"""agent BC의 llm_usage·analysis_report를 읽기 전용으로 조회한다 (cross-BC 접근은 이 구현체 안에서만)."""

from datetime import datetime

from sqlalchemy import text

from apps.ops.app.dtos.healthcare_dto import RecentAnalysisDto
from apps.ops.app.ports.output.healthcare_port import LlmUsagePort
from apps.ops.domain.services.usage_series import TimedUsage
from apps.ops.domain.services.usage_stats import LlmUsageRecord
from core.matrix.grid_oracle_database_manager import session_scope


class LlmUsageGateway(LlmUsagePort):
    def records_since(self, since: datetime) -> list[LlmUsageRecord]:
        with session_scope() as session:
            rows = session.execute(
                text(
                    "select model, input_tokens, output_tokens, latency_ms from llm_usage where created_at >= :since"
                ),
                {"since": since},
            )
            return [LlmUsageRecord(*row) for row in rows]

    def timed_since(self, since: datetime) -> list[TimedUsage]:
        with session_scope() as session:
            rows = session.execute(
                text("select created_at, input_tokens + output_tokens from llm_usage where created_at >= :since"),
                {"since": since},
            )
            return [TimedUsage(at, tokens) for at, tokens in rows]

    def recent_analyses(self, limit: int) -> list[RecentAnalysisDto]:
        with session_scope() as session:
            rows = session.execute(
                text(
                    """
                    select r.id, r.region_code, r.industry, u.model, u.input_tokens, u.output_tokens,
                           u.latency_ms, u.created_at
                    from llm_usage u join analysis_report r on r.id = u.analysis_id
                    order by u.created_at desc
                    limit :limit
                    """
                ),
                {"limit": limit},
            )
            return [RecentAnalysisDto(*row) for row in rows]
