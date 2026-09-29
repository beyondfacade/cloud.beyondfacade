"""Driven Adapter — 아파트 매매 건수(housing BC)를 행정동으로 배분 (업종 특화 신호 설계서 §11).
가중치 = store 전 업종 점포의 (구, 법정동) → 행정동 분포. cross-BC 접근은 이 파일 안에서만."""

from collections import defaultdict
from functools import cached_property

from sqlalchemy import func, select

from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.app.ports.output.region_industry_verdict_port import TradeCountsPort
from apps.verdict.domain.services.legal_dong import allocate, legal_dong_of
from core.matrix.grid_oracle_database_manager import session_scope


class AptTradeGateway(TradeCountsPort):
    @cached_property
    def _weights(self) -> dict[tuple[str, str], dict[str, int]]:
        with session_scope() as session:
            rows = session.execute(
                select(StoreOrm.district_code, StoreOrm.jibun_address, StoreOrm.region_code)
                .where(StoreOrm.region_code.is_not(None), StoreOrm.jibun_address.is_not(None))
            ).all()
        weights: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for district, address, region in rows:
            dong = legal_dong_of(address)
            if dong is not None:
                weights[(district, dong)][region] += 1
        return weights

    def trades_by_region(self, month_from: str, month_to: str) -> dict[str, float]:
        A = AptTradeCountOrm
        with session_scope() as session:
            rows = session.execute(
                select(A.district_code, A.legal_dong, func.sum(A.trade_count))
                .where(A.deal_ym >= month_from, A.deal_ym <= month_to)
                .group_by(A.district_code, A.legal_dong)
            ).all()
        return allocate({(d, dong): int(n) for d, dong, n in rows}, self._weights)
