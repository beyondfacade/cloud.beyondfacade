"""analysis_pending 저장소 — 워커(프로세스)가 여럿이어도 POST와 SSE가 같은 장부를 본다."""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from apps.agent.adapter.outbound.orm_mappers.analysis_pending_orm_mapper import to_entity, to_orm
from apps.agent.adapter.outbound.orms.analysis_pending_orm import (
    FK_INDUSTRY,
    FK_REGION,
    AnalysisPendingOrm,
)
from apps.agent.app.ports.output.analysis_pending_port import (
    AnalysisTargetNotFound,
    PendingAnalysisPort,
)
from apps.agent.domain.entities.analysis_pending_entity import PENDING_TTL, PendingAnalysis
from core.matrix.grid_oracle_database_manager import session_scope

# FK 제약 이름 → (어긋난 필드, 엔티티 속성) — 무결성 오류를 포트 예외로 옮긴다
_FK_FIELD = {FK_REGION: ("region", "region_code"), FK_INDUSTRY: ("industry", "industry_id")}


def _cutoff() -> datetime:
    return datetime.now(UTC) - PENDING_TTL


class SqlAlchemyPendingAnalysisRepository(PendingAnalysisPort):
    def save(self, pending: PendingAnalysis) -> None:
        try:
            with session_scope() as session:
                # 버려진 주문 정리는 저장이 같이 맡는다 — created_at 인덱스로 가볍다, 크론을 따로 두지 않는다
                session.execute(delete(AnalysisPendingOrm).where(AnalysisPendingOrm.created_at < _cutoff()))
                session.add(to_orm(pending))
        except IntegrityError as error:
            target = _FK_FIELD.get(getattr(getattr(error.orig, "diag", None), "constraint_name", None))
            if target is None:
                raise
            field, attribute = target
            raise AnalysisTargetNotFound(field, getattr(pending, attribute)) from error

    def find(self, analysis_id: str) -> PendingAnalysis | None:
        with session_scope() as session:
            orm = session.scalar(
                select(AnalysisPendingOrm).where(
                    AnalysisPendingOrm.analysis_id == analysis_id,
                    AnalysisPendingOrm.created_at >= _cutoff(),
                )
            )
            return to_entity(orm) if orm is not None else None

    def delete(self, analysis_id: str) -> None:
        with session_scope() as session:
            session.execute(delete(AnalysisPendingOrm).where(AnalysisPendingOrm.analysis_id == analysis_id))
