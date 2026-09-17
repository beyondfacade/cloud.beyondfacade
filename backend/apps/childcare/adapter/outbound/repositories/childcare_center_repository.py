from datetime import date

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import insert

from apps.childcare.adapter.outbound.orm_mappers.childcare_center_orm_mapper import to_entity
from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.childcare.app.ports.output.childcare_center_port import (
    ChildcareCenterQueryRepositoryPort,
    ChildcareSnapshotRepositoryPort,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from core.matrix.grid_oracle_database_manager import session_scope

# 재수집 시 덮어쓰지 않는 컬럼 — PK, 최초 관측일, 공간조인이 기입한 region_code
_PRESERVED_CENTER_COLUMNS = ("center_id", "first_seen_on", "region_code")


def operating_centers_with_latest_stat(region_code: str) -> Select:
    """행정동의 운영 중 시설 × 시설별 최신 현황 — 조회 리포지토리 2종이 공유하는 조인.

    운영 중 = 자치구 최신 관측일(max last_seen_on)에 관측된 시설. 전역 최대가 아니라 자치구 단위라
    한 구의 수집이 실패해도 그 구 시설이 이전 스냅샷 그대로 남는다.
    """
    district_latest = (
        select(
            ChildcareCenterOrm.district_code,
            func.max(ChildcareCenterOrm.last_seen_on).label("seen_on"),
        )
        .group_by(ChildcareCenterOrm.district_code)
        .subquery()
    )
    stat_latest = (
        select(
            ChildcareCenterStatOrm.center_id,
            func.max(ChildcareCenterStatOrm.base_date).label("base_date"),
        )
        .group_by(ChildcareCenterStatOrm.center_id)
        .subquery()
    )
    return (
        select(ChildcareCenterOrm, ChildcareCenterStatOrm)
        .join(
            district_latest,
            and_(
                district_latest.c.district_code == ChildcareCenterOrm.district_code,
                district_latest.c.seen_on == ChildcareCenterOrm.last_seen_on,
            ),
        )
        .join(stat_latest, stat_latest.c.center_id == ChildcareCenterOrm.center_id)
        .join(
            ChildcareCenterStatOrm,
            and_(
                ChildcareCenterStatOrm.center_id == stat_latest.c.center_id,
                ChildcareCenterStatOrm.base_date == stat_latest.c.base_date,
            ),
        )
        .where(ChildcareCenterOrm.region_code == region_code)
        .order_by(ChildcareCenterOrm.center_id)
    )


def _center_values(center: ChildcareCenter, observed_on: date) -> dict:
    return {
        "center_id": center.center_id,
        "name": center.name,
        "type_name": center.type_name,
        "status_name": center.status_name,
        "district_code": center.district_code,
        "address": center.address,
        "zipcode": center.zipcode,
        "tel": center.tel,
        "lat": center.lat,
        "lng": center.lng,
        "approved_on": center.approved_on,
        "paused_from": center.paused_from,
        "paused_until": center.paused_until,
        "abolished_on": center.abolished_on,
        "first_seen_on": observed_on,
        "last_seen_on": observed_on,
    }


def _stat_values(center: ChildcareCenter) -> dict:
    stat = center.stat
    return {
        "center_id": center.center_id,
        "base_date": stat.base_date,
        "capacity": stat.capacity,
        "child_count": stat.child_count,
        "waiting_count": stat.waiting_count,
        "class_count": stat.class_count,
        "staff_count": stat.staff_count,
    }


class SqlAlchemyChildcareCenterRepository(
    ChildcareSnapshotRepositoryPort, ChildcareCenterQueryRepositoryPort
):
    def upsert(self, centers: list[ChildcareCenter], observed_on: date) -> int:
        if not centers:
            return 0
        deduped = list({c.center_id: c for c in centers}.values())
        center_statement = insert(ChildcareCenterOrm).values(
            [_center_values(c, observed_on) for c in deduped]
        )
        stat_statement = insert(ChildcareCenterStatOrm).values([_stat_values(c) for c in deduped])
        with session_scope() as session:
            session.execute(
                center_statement.on_conflict_do_update(
                    index_elements=["center_id"],
                    set_={
                        column: getattr(center_statement.excluded, column)
                        for column in _center_values(deduped[0], observed_on)
                        if column not in _PRESERVED_CENTER_COLUMNS
                    },
                )
            )
            session.execute(
                stat_statement.on_conflict_do_update(
                    index_elements=["center_id", "base_date"],
                    set_={
                        column: getattr(stat_statement.excluded, column)
                        for column in _stat_values(deduped[0])
                        if column not in ("center_id", "base_date")
                    },
                )
            )
        return len(deduped)

    def list_operating(self, region_code: str) -> list[ChildcareCenter]:
        statement = operating_centers_with_latest_stat(region_code).where(
            ChildcareCenterOrm.lat.is_not(None), ChildcareCenterOrm.lng.is_not(None)
        )
        with session_scope() as session:
            return [to_entity(center, stat) for center, stat in session.execute(statement).all()]
