"""대기 분석 장부(analysis_pending) — 워커가 여럿이어도 POST·GET이 같은 장부를 본다."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from apps.agent.adapter.outbound.repositories.analysis_pending_repository import (
    SqlAlchemyPendingAnalysisRepository,
)
from apps.agent.domain.entities.analysis_pending_entity import PENDING_TTL, PendingAnalysis
from core.matrix.grid_oracle_database_manager import session_scope


def _pending(created_at: datetime) -> PendingAnalysis:
    return PendingAnalysis(
        analysis_id=uuid.uuid4().hex,
        region_code="1168064000",
        industry_id="cafe",
        question="괜찮을까요?",
        model="hybrid",
        budget=50_000_000,
        created_at=created_at,
    )


def test_저장한_대기_분석은_다른_저장소_인스턴스에서도_찾는다():
    """다른 워커 = 다른 프로세스·다른 인스턴스 — 메모리가 아니라 DB에서 찾아야 한다."""
    pending = _pending(datetime.now(UTC))
    SqlAlchemyPendingAnalysisRepository().save(pending)

    assert SqlAlchemyPendingAnalysisRepository().find(pending.analysis_id) == pending


def test_수명이_지난_대기_분석은_없는_것으로_본다():
    stale = _pending(datetime.now(UTC) - PENDING_TTL - timedelta(minutes=1))
    SqlAlchemyPendingAnalysisRepository().save(stale)

    assert SqlAlchemyPendingAnalysisRepository().find(stale.analysis_id) is None


def test_저장할_때_수명이_지난_행을_함께_지운다():
    repository = SqlAlchemyPendingAnalysisRepository()
    stale = _pending(datetime.now(UTC) - PENDING_TTL - timedelta(minutes=1))
    repository.save(stale)

    repository.save(_pending(datetime.now(UTC)))

    with session_scope() as session:
        left = session.execute(
            text("select count(*) from analysis_pending where analysis_id = :id"), {"id": stale.analysis_id}
        ).scalar()
    assert left == 0
