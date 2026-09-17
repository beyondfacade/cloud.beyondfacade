"""Driven Adapters — 스냅샷 원천 현행 점포수 (cross-BC 접근은 어댑터 레이어에서만).

현행 판정은 각 BC 조회 API와 동일하다 — 지도 요약 카드와 단계구분도 점포수가 어긋나지 않게 한다.
- 어린이집: 자치구 최신 관측일에 관측된 시설 (수집 단위 = 자치구)
- 편의점: 행정동 최신 관측일에 관측된 점포 (수집 단위 = 행정동)
"""

from sqlalchemy import and_, func, select

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.convenience.adapter.outbound.orms.convenience_store_orm import ConvenienceStoreOrm
from apps.metric.app.dtos.region_industry_metric_dto import SnapshotStoreCount
from apps.metric.app.ports.output.region_industry_metric_port import SnapshotStoreCountPort
from core.matrix.grid_oracle_database_manager import session_scope


class ChildcareStoreCountGateway(SnapshotStoreCountPort):
    def current_counts(self) -> list[SnapshotStoreCount]:
        latest = (
            select(
                ChildcareCenterOrm.district_code,
                func.max(ChildcareCenterOrm.last_seen_on).label("seen_on"),
            )
            .group_by(ChildcareCenterOrm.district_code)
            .subquery()
        )
        statement = (
            select(
                ChildcareCenterOrm.region_code,
                func.extract("year", ChildcareCenterOrm.last_seen_on),
                func.count(),
            )
            .join(
                latest,
                and_(
                    latest.c.district_code == ChildcareCenterOrm.district_code,
                    latest.c.seen_on == ChildcareCenterOrm.last_seen_on,
                ),
            )
            .where(ChildcareCenterOrm.region_code.is_not(None))
            .group_by(ChildcareCenterOrm.region_code, ChildcareCenterOrm.last_seen_on)
        )
        with session_scope() as session:
            return [
                SnapshotStoreCount(region_code, "childcare", int(year), count)
                for region_code, year, count in session.execute(statement).all()
            ]


class ConvenienceStoreCountGateway(SnapshotStoreCountPort):
    def current_counts(self) -> list[SnapshotStoreCount]:
        latest = (
            select(
                ConvenienceStoreOrm.region_code,
                func.max(ConvenienceStoreOrm.last_seen_on).label("seen_on"),
            )
            .group_by(ConvenienceStoreOrm.region_code)
            .subquery()
        )
        statement = (
            select(
                ConvenienceStoreOrm.region_code,
                func.extract("year", ConvenienceStoreOrm.last_seen_on),
                func.count(),
            )
            .join(
                latest,
                and_(
                    latest.c.region_code == ConvenienceStoreOrm.region_code,
                    latest.c.seen_on == ConvenienceStoreOrm.last_seen_on,
                ),
            )
            .group_by(ConvenienceStoreOrm.region_code, ConvenienceStoreOrm.last_seen_on)
        )
        with session_scope() as session:
            return [
                SnapshotStoreCount(region_code, "convenience_store", int(year), count)
                for region_code, year, count in session.execute(statement).all()
            ]
