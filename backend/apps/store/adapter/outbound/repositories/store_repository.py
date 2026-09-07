from datetime import datetime

from sqlalchemy import func, select

from apps.store.adapter.outbound.orm_mappers.store_orm_mapper import to_entity, to_orm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.app.ports.output.store_port import StoreRepositoryPort
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyStoreRepository(StoreRepositoryPort):
    def upsert(self, stores: list[Store]) -> int:
        if not stores:
            return 0
        deduped = {s.store_id: s for s in stores}  # 배치 내 동일 관리번호는 마지막 것만
        with session_scope() as session:
            for store in deduped.values():
                session.merge(to_orm(store))
        return len(deduped)

    def latest_source_updated_at(
        self, industry_id: str, district_code: str
    ) -> datetime | None:
        with session_scope() as session:
            return session.execute(
                select(func.max(StoreOrm.source_updated_at)).where(
                    StoreOrm.industry_id == industry_id,
                    StoreOrm.district_code == district_code,
                )
            ).scalar()

    def list_open(self, region_code: str, industry_id: str) -> list[Store]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(StoreOrm)
                    .where(
                        StoreOrm.region_code == region_code,
                        StoreOrm.industry_id == industry_id,
                        StoreOrm.close_date.is_(None),
                        StoreOrm.lat.is_not(None),
                        StoreOrm.lng.is_not(None),
                    )
                    .order_by(StoreOrm.store_id)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]
