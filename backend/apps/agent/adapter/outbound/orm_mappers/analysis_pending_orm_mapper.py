"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.agent.adapter.outbound.orms.analysis_pending_orm import AnalysisPendingOrm
from apps.agent.domain.entities.analysis_pending_entity import PendingAnalysis


def to_orm(pending: PendingAnalysis) -> AnalysisPendingOrm:
    return AnalysisPendingOrm(
        analysis_id=pending.analysis_id,
        region_code=pending.region_code,
        industry_id=pending.industry_id,
        question=pending.question,
        model=pending.model,
        budget=pending.budget,
        created_at=pending.created_at,
    )


def to_entity(orm: AnalysisPendingOrm) -> PendingAnalysis:
    return PendingAnalysis(
        analysis_id=orm.analysis_id,
        region_code=orm.region_code,
        industry_id=orm.industry_id,
        question=orm.question,
        model=orm.model,
        budget=orm.budget,
        created_at=orm.created_at,
    )
