from datetime import date, datetime

from sqlalchemy import and_, func, or_, select, update

from apps.store.adapter.outbound.orm_mappers.store_orm_mapper import to_entity, to_orm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.app.ports.output.broker_snapshot_port import StoreSnapshotRepositoryPort
from apps.store.app.ports.output.store_geocode_port import StoreGeocodeRepositoryPort
from apps.store.app.ports.output.store_port import StoreRepositoryPort
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyStoreRepository(
    StoreRepositoryPort, StoreSnapshotRepositoryPort, StoreGeocodeRepositoryPort
):
    def upsert(self, stores: list[Store]) -> int:
        if not stores:
            return 0
        deduped = {s.store_id: s for s in stores}  # 배치 내 동일 관리번호는 마지막 것만
        with session_scope() as session:
            for store in deduped.values():
                orm = to_orm(store)
                existing = session.get(StoreOrm, store.store_id)
                # 원천에 좌표가 없는 업종(학원·중개) — 재수집이 지오코딩·공간조인 결과를 지우지 않음
                if existing is not None and orm.lat is None and existing.lat is not None:
                    orm.lat = existing.lat
                    orm.lng = existing.lng
                    if orm.region_code is None:
                        orm.region_code = existing.region_code
                session.merge(orm)
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

    def active_store_ids(self, industry_id: str, district_code: str) -> set[str]:
        with session_scope() as session:
            rows = session.execute(
                select(StoreOrm.store_id).where(
                    StoreOrm.industry_id == industry_id,
                    StoreOrm.district_code == district_code,
                    StoreOrm.close_date.is_(None),
                )
            ).scalars()
            return set(rows)

    def existing_locations(
        self, industry_id: str, district_code: str
    ) -> dict[str, tuple[float, float, str | None]]:
        with session_scope() as session:
            rows = session.execute(
                select(
                    StoreOrm.store_id, StoreOrm.lat, StoreOrm.lng, StoreOrm.region_code
                ).where(
                    StoreOrm.industry_id == industry_id,
                    StoreOrm.district_code == district_code,
                    StoreOrm.lat.is_not(None),
                )
            ).all()
            return {row.store_id: (row.lat, row.lng, row.region_code) for row in rows}

    def mark_closed(
        self, store_ids: list[str], close_date: date, status_code: str, status_name: str
    ) -> int:
        if not store_ids:
            return 0
        with session_scope() as session:
            result = session.execute(
                update(StoreOrm)
                .where(StoreOrm.store_id.in_(store_ids), StoreOrm.close_date.is_(None))
                .values(
                    close_date=close_date,
                    status_code=status_code,
                    status_name=status_name,
                )
            )
            return result.rowcount

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

    def list_pending(
        self, industry_ids: list[str], limit: int | None = None
    ) -> list[Store]:
        if not industry_ids:
            return []
        with session_scope() as session:
            stmt = (
                select(StoreOrm)
                .where(
                    StoreOrm.industry_id.in_(industry_ids),
                    StoreOrm.lat.is_(None),
                    or_(
                        StoreOrm.road_address.is_not(None),
                        StoreOrm.jibun_address.is_not(None),
                    ),
                )
                .order_by(StoreOrm.store_id)
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [to_entity(row) for row in rows]

    def update_coordinates(
        self, updates: list[tuple[str, float, float]]
    ) -> int:
        if not updates:
            return 0
        with session_scope() as session:
            count = 0
            for store_id, lat, lng in updates:
                result = session.execute(
                    update(StoreOrm)
                    .where(
                        and_(StoreOrm.store_id == store_id, StoreOrm.lat.is_(None))
                    )
                    .values(lat=lat, lng=lng)
                )
                count += result.rowcount
            return count
