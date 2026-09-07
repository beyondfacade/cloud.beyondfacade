from datetime import date

from sqlalchemy import select, update

from apps.funding.adapter.outbound.orm_mappers.funding_program_orm_mapper import (
    apply_to_orm,
    to_entity,
    to_orm,
)
from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.funding.app.ports.output.funding_program_port import FundingProgramRepositoryPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyFundingProgramRepository(FundingProgramRepositoryPort):
    def upsert(self, programs: list[FundingProgram]) -> tuple[int, int]:
        if not programs:
            return 0, 0
        # dict — 같은 배치 안의 중복 program_id 제거 (news BC 관행)
        batch = {p.program_id: p for p in programs}
        inserted = updated = 0
        with session_scope() as session:
            existing = {
                orm.program_id: orm
                for orm in session.execute(
                    select(FundingProgramOrm).where(
                        FundingProgramOrm.program_id.in_(batch.keys())
                    )
                ).scalars()
            }
            for program_id, program in batch.items():
                orm = existing.get(program_id)
                if orm is None:
                    session.add(to_orm(program))
                    inserted += 1
                elif orm.source_updated_at != program.source_updated_at:
                    apply_to_orm(program, orm)
                    updated += 1
        return inserted, updated

    def refresh_expirations(self, today: date) -> int:
        with session_scope() as session:
            expired = session.execute(
                update(FundingProgramOrm)
                .where(
                    FundingProgramOrm.deadline < today,
                    FundingProgramOrm.is_expired.is_(False),
                )
                .values(is_expired=True)
            ).rowcount
            # 마감 연장(변경 공고)·상시 전환 복원 — 만료 플래그는 항상 deadline과 정합
            session.execute(
                update(FundingProgramOrm)
                .where(
                    FundingProgramOrm.is_expired.is_(True),
                    (FundingProgramOrm.deadline >= today)
                    | (FundingProgramOrm.deadline.is_(None)),
                )
                .values(is_expired=False)
            )
        return expired

    def list_open(self, limit: int) -> list[FundingProgram]:
        with session_scope() as session:
            orms = session.execute(
                select(FundingProgramOrm)
                .where(FundingProgramOrm.is_expired.is_(False))
                .order_by(
                    FundingProgramOrm.deadline.asc().nulls_last(),  # 상시(None)는 뒤
                    FundingProgramOrm.program_id,
                )
                .limit(limit)
            ).scalars()
            return [to_entity(orm) for orm in orms]
