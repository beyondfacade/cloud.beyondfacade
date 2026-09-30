"""Driven Adapter — store 원천 테이블의 서울 전체 업종별 월 개폐업 (cross-BC 접근은 어댑터 레이어에서만)."""

from datetime import date

from sqlalchemy import func, select

from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.shock.app.ports.output.event_analog_port import StoreFlowPort
from apps.shock.domain.services.industry_flows import IndustryFlows
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

# 흐름을 비교할 수 없는 원천 — 학원은 폐원일이 없고, 어린이집·편의점은 스냅샷이며,
# 치킨은 2017년 이후 신규 인허가가 없어(다른 인허가로 옮겨 감) 개업 0이 값처럼 보인다.
# 부동산중개·기타음식점은 한 업종으로 읽을 수 없는 묶음이다.
_EXCLUDED = ("academy", "childcare", "convenience_store", "chicken", "real_estate", "restaurant_other")


def _month(day) -> date:
    return date(day.year, day.month, 1)


class StoreFlowGateway(StoreFlowPort):
    def monthly_flows(self) -> list[IndustryFlows]:
        with session_scope() as session:
            names = dict(session.execute(select(IndustryOrm.industry_id, IndustryOrm.name)).all())
            opened = func.date_trunc("month", StoreOrm.open_date)
            closed = func.date_trunc("month", StoreOrm.close_date)
            openings = session.execute(
                select(StoreOrm.industry_id, opened, func.count())
                .where(StoreOrm.open_date.is_not(None), StoreOrm.industry_id.not_in(_EXCLUDED))
                .group_by(StoreOrm.industry_id, opened)
            ).all()
            # 개업일 없는 폐업은 점포수 누적에서 빼기만 하게 된다 — 개업일이 있는 점포만 센다
            closings = session.execute(
                select(StoreOrm.industry_id, closed, func.count())
                .where(
                    StoreOrm.close_date.is_not(None),
                    StoreOrm.open_date.is_not(None),
                    StoreOrm.industry_id.not_in(_EXCLUDED),
                )
                .group_by(StoreOrm.industry_id, closed)
            ).all()
        by_industry: dict[str, tuple[dict[date, int], dict[date, int]]] = {}
        for industry_id, month, count in openings:
            by_industry.setdefault(industry_id, ({}, {}))[0][_month(month)] = count
        for industry_id, month, count in closings:
            by_industry.setdefault(industry_id, ({}, {}))[1][_month(month)] = count
        return [
            IndustryFlows(industry_id, names.get(industry_id, industry_id), opens, closes)
            for industry_id, (opens, closes) in sorted(by_industry.items())
        ]
