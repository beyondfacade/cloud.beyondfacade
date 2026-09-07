from datetime import date

from sqlalchemy.dialects.postgresql import insert

from apps.convenience.adapter.outbound.orms.convenience_store_orm import (
    ConvenienceStoreOrm,
)
from apps.convenience.app.ports.output.convenience_store_port import (
    ConvenienceSnapshotRepositoryPort,
)
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore
from core.matrix.grid_oracle_database_manager import session_scope


def _row_values(store: ConvenienceStore, observed_on: date) -> dict:
    return {
        "store_id": store.store_id,
        "name": store.name,
        "branch_name": store.branch_name,
        "brand": store.brand,
        "region_code": store.region_code,
        "lat": store.lat,
        "lng": store.lng,
        "road_address": store.road_address,
        "jibun_address": store.jibun_address,
        "source_stdr_ym": store.source_stdr_ym,
        "first_seen_on": observed_on,
        "last_seen_on": observed_on,
    }


class SqlAlchemyConvenienceStoreRepository(ConvenienceSnapshotRepositoryPort):
    def upsert(self, stores: list[ConvenienceStore], observed_on: date) -> int:
        """PK(bizesId) 멱등 업서트 — 기존 행은 first_seen_on(최초 관측)만 보존하고
        원천 컬럼·last_seen_on을 갱신. 소실 행은 건드리지 않아 last_seen_on이 멈춘다."""
        if not stores:
            return 0
        deduped = {s.store_id: s for s in stores}  # 배치 내 동일 업소번호는 마지막 것만
        statement = insert(ConvenienceStoreOrm).values(
            [_row_values(s, observed_on) for s in deduped.values()]
        )
        with session_scope() as session:
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=["store_id"],
                    set_={
                        column: getattr(statement.excluded, column)
                        for column in _row_values(next(iter(deduped.values())), observed_on)
                        if column not in ("store_id", "first_seen_on")
                    },
                )
            )
        return len(deduped)
