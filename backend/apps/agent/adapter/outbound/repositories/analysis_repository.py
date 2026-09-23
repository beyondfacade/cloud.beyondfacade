"""analysis_report·llm_usage 저장소."""

import json

from apps.agent.adapter.outbound.orms.analysis_report_orm import AnalysisReportOrm
from apps.agent.adapter.outbound.orms.llm_usage_orm import LlmUsageOrm
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAnalysisRepository:
    def save_report(
        self,
        *,
        analysis_id: str,
        region_code: str,
        industry: str,
        question: str | None,
        report_md: str,
        citations: list[dict],
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
    ) -> None:
        with session_scope() as session:
            session.add(
                AnalysisReportOrm(
                    id=analysis_id,
                    region_code=region_code,
                    industry=industry,
                    question=question,
                    report_md=report_md,
                    citations_json=json.dumps(citations, ensure_ascii=False),
                    model=model,
                )
            )
            session.add(
                LlmUsageOrm(
                    analysis_id=analysis_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                )
            )
