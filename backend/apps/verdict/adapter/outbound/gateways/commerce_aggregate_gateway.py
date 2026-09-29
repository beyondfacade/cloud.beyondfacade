"""Driven Adapter — 집계 원천: 서울시 상권분석 동×분기 점포·폐업 수 (업종 특화 신호 설계서 §7). 개별 점포 이력이 없는 업종(부동산).
업종 ↔ 서비스업종 코드는 industry_source_code(source_system='seoul_commercial'), 코드·상권코드가 여럿이면 동 단위로 합한다.
cross-BC 접근(commerce·master ORM)은 이 파일 안에서만."""

from collections.abc import Iterable
from datetime import date, timedelta
from functools import cached_property

from sqlalchemy import func, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort
from apps.verdict.domain.services.backtest import quarter_before, quarter_of, shift_quarter
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCE_SYSTEM = "seoul_commercial"
_WINDOW_QUARTERS = 4  # 폐업률 창 — 12개월 창과 같은 길이

S = RegionCommerceStoreOrm


class CommerceAggregateSignalData(IndustrySignalDataPort):
    def __init__(self, industry_ids: Iterable[str]) -> None:
        self._industry_ids = tuple(industry_ids)

    @cached_property
    def _industry_of_code(self) -> dict[str, str]:
        with session_scope() as session:
            rows = session.execute(
                select(IndustrySourceCodeOrm.code, IndustrySourceCodeOrm.industry_id).where(
                    IndustrySourceCodeOrm.source_system == _SOURCE_SYSTEM,
                    IndustrySourceCodeOrm.industry_id.in_(self._industry_ids),
                )
            ).all()
        return dict(rows)

    @cached_property
    def _quarters(self) -> list[str]:
        with session_scope() as session:
            return list(
                session.execute(
                    select(S.year_quarter).where(S.service_industry_code.in_(self._industry_of_code))
                    .distinct().order_by(S.year_quarter)
                ).scalars()
            )

    def _latest_at_or_before(self, quarter: str | None) -> str | None:
        eligible = [q for q in self._quarters if quarter is None or q <= quarter]
        return eligible[-1] if eligible else None

    def _between(self, after: str, upto: str) -> list[str]:
        return [q for q in self._quarters if after < q <= upto]

    def _sum(self, column, quarters: list[str]) -> dict[tuple[str, str], int]:
        """(동, 업종)별 column 합 — 주어진 분기들. 동 미배정 행은 뺀다."""
        if not quarters:
            return {}
        with session_scope() as session:
            rows = session.execute(
                select(S.region_code, S.service_industry_code, func.coalesce(func.sum(column), 0))
                .where(
                    S.region_code.is_not(None),
                    S.service_industry_code.in_(self._industry_of_code),
                    S.year_quarter.in_(quarters),
                )
                .group_by(S.region_code, S.service_industry_code)
            ).all()
        acc: dict[tuple[str, str], int] = {}
        for region, code, total in rows:
            key = (region, self._industry_of_code[code])
            acc[key] = acc.get(key, 0) + int(total)
        return acc

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """폐업률 재료 — (q0, q_last] 폐업·개업 합과 q0 점포수 (설계서 §7-1). 코호트 항목은 원천에 없어 0."""
        last = self._latest_at_or_before(quarter_before(today))
        if last is None:
            return []
        first = shift_quarter(last, -_WINDOW_QUARTERS)
        window = self._between(first, last)
        start = self._sum(S.store_count, [first])
        closed = self._sum(S.close_store_count, window)
        opened = self._sum(S.open_store_count, window)
        return [
            StoreSignalStat(region, industry, start.get((region, industry), 0), opened.get((region, industry), 0),
                            closed.get((region, industry), 0), 0, 0, 0, None)
            for region, industry in sorted(start.keys() | closed.keys())
        ]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """포화 분자 — quarter_max 이하 최신 분기 점포수. 분기 원천이라 연도 상한(year_max)보다 촘촘한 quarter_max만 본다."""
        at = self._latest_at_or_before(quarter_max)
        if at is None:
            return []
        return [LatestStoreCount(r, i, n) for (r, i), n in sorted(self._sum(S.store_count, [at]).items())]

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        """재고 결과 (설계서 §7-3) — opened = as_of 분기 점포수, closed_within = 다음 분기 ~ as_of+horizon 분기 폐업 합.
        개별 개업일이 없어 진입 코호트를 만들 수 없다 — entry_days는 쓰지 않는다."""
        exposure_quarter = quarter_of(as_of)
        horizon_quarter = quarter_of(as_of + timedelta(days=horizon_days))
        exposure = self._sum(S.store_count, [exposure_quarter])
        closed = self._sum(S.close_store_count, self._between(exposure_quarter, horizon_quarter))
        return [EntrantOutcome(r, i, n, closed.get((r, i), 0)) for (r, i), n in sorted(exposure.items())]
