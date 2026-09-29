"""Driven Adapter — 편의점 개폐업 대리 원천: 담배소매인 인허가 중 편의점 상호 (업종 특화 신호 설계서 §5·§6).
창 집계는 StoreSignalStatsGateway의 SQL과 한 줄씩 대응한다 — 원천만 다르고 신호 정의는 같다.
cross-BC 접근(tobacco·store ORM)은 이 파일 안에서만. 원천이 정적 아카이브라 기준일 = min(요청일, 원천 최신 날짜).

폐업 계열 상태인데 종료일(폐업일·취소일)이 없는 행은 적재 시점에 뺀다 — 안 빼면 영구 영업으로 잡혀 편의점
에피소드·담배권 빈자리 둘 다 틀어진다(실측 9/29: 730행, 그중 편의점 상호 55행. §17 진행 기록)."""

import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import replace
from datetime import date, timedelta
from functools import cached_property

from sqlalchemy import and_, or_, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort
from apps.verdict.domain.services.convenience_history import (
    Episode,
    RetailerRecord,
    address_key,
    brand_of,
    fold_successions,
)
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M, GeoPoint, blocked_counts
from core.matrix.grid_oracle_database_manager import session_scope

_DAYS_PER_MONTH = 30.4375
_THREE_YEARS_DAYS = 3 * 365
# 폐업처리(2)·직권취소(3)·임시소매기간만료(4)·지정취소(5) — 종료를 뜻하는 상태인데 폐업일·취소일이 둘 다 없는 행은
# 원천 결측이라 뺀다. 정상영업(0)·휴업처리(1)·영업정지(6)는 살아있을 수 있는 상태라 그대로 둔다.
_ENDED_STATUS_CODES = ("2", "3", "4", "5")


def _active(open_date: date, close_date: date | None, at: date) -> bool:
    return open_date <= at and (close_date is None or close_date > at)


def stats_from_episodes(episodes: Iterable[Episode], today: date, industry_id: str) -> list[StoreSignalStat]:
    """동별 창 집계 — StoreSignalStatsGateway.signal_stats와 같은 규칙 (판정 카드 설계서 §3-1).
    12개월 전 영업 / 12개월 개·폐업 / [today−4y, today−3y) 코호트·3년 생존 / 최근 3년 폐업 영업개월 중위(폐업일<개업일 제외)."""
    since_12m = today - timedelta(days=365)
    cohort_to = today - timedelta(days=3 * 365)
    cohort_from = today - timedelta(days=4 * 365)
    acc: dict[str, dict] = defaultdict(
        lambda: {"start": 0, "opened": 0, "closed": 0, "cohort": 0, "survived": 0, "months": []}
    )
    for e in episodes:
        a = acc[e.region_code]
        days_open = None if e.close_date is None else (e.close_date - e.open_date).days
        in_cohort = cohort_from <= e.open_date < cohort_to
        a["start"] += e.open_date <= since_12m and (e.close_date is None or e.close_date > since_12m)
        a["opened"] += since_12m < e.open_date <= today
        a["closed"] += e.close_date is not None and since_12m < e.close_date <= today
        a["cohort"] += in_cohort
        a["survived"] += in_cohort and (days_open is None or days_open >= _THREE_YEARS_DAYS)
        if e.close_date is not None and cohort_to <= e.close_date <= today and days_open >= 0:
            a["months"].append(days_open / _DAYS_PER_MONTH)
    return [
        StoreSignalStat(
            region, industry_id, a["start"], a["opened"], a["closed"], a["cohort"], a["survived"],
            len(a["months"]), statistics.median(a["months"]) if a["months"] else None,
        )
        for region, a in sorted(acc.items())
    ]


class TobaccoConvenienceSignalData(IndustrySignalDataPort):
    def __init__(self, industry_id: str = "convenience_store", radius_m: float = TOBACCO_GAP_RADIUS_M) -> None:
        self._industry_id = industry_id
        self._radius_m = radius_m

    @cached_property
    def _rows(self) -> list:
        T = TobaccoRetailerOrm
        # 종료 상태인데 종료일이 둘 다 없는 유령 행은 여기서 뺀다 — 이후 모든 파생(레코드·에피소드·빈자리)이 이 목록만 본다.
        phantom = and_(T.status_code.in_(_ENDED_STATUS_CODES), T.close_date.is_(None), T.cancel_date.is_(None))
        with session_scope() as session:
            return session.execute(
                select(
                    T.retailer_id, T.name, T.region_code, T.designated_date, T.permit_date, T.close_date,
                    T.cancel_date, T.jibun_address, T.lat, T.lng,
                ).where(~phantom)
            ).all()

    @cached_property
    def _records(self) -> list[RetailerRecord]:
        return [
            RetailerRecord(
                r.retailer_id, r.name, r.region_code, r.designated_date or r.permit_date,
                r.close_date or r.cancel_date, address_key(r.jibun_address),
            )
            for r in self._rows
        ]

    @cached_property
    def _latest(self) -> date:
        """원천 최신 날짜 — 정적 아카이브(2026-08 확보)라 오늘보다 앞선다 (설계서 §5-3)."""
        return max(d for r in self._records for d in (r.open_date, r.close_date) if d is not None)

    @cached_property
    def _episodes(self) -> list[Episode]:
        return fold_successions(r for r in self._records if brand_of(r.name) is not None)

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        anchor = min(today, self._latest)
        stats = {s.region_code: s for s in stats_from_episodes(self._episodes, anchor, self._industry_id)}
        gaps = self._gaps(anchor)
        empty = StoreSignalStat("", self._industry_id, 0, 0, 0, 0, 0, 0, None)
        return [
            replace(
                stats.get(region, replace(empty, region_code=region)),
                gap_candidates=gaps.get(region, (0, 0))[0],
                gap_blocked=gaps.get(region, (0, 0))[1],
            )
            for region in sorted(stats.keys() | gaps.keys())
        ]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """기준일에 영업 중인 에피소드 수 — 배치는 원천 최신 날짜, 백테스트는 year_max년 말 (설계서 §5-3)."""
        at = self._latest if year_max is None else date(year_max, 12, 31)
        counts = Counter(e.region_code for e in self._episodes if _active(e.open_date, e.close_date, at))
        return [LatestStoreCount(region, self._industry_id, n) for region, n in sorted(counts.items())]

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        entry_end = as_of + timedelta(days=entry_days)
        for e in self._episodes:
            if as_of <= e.open_date < entry_end:
                cell = acc[e.region_code]
                cell[0] += 1
                cell[1] += e.close_date is not None and 0 <= (e.close_date - e.open_date).days <= horizon_days
        return [EntrantOutcome(region, self._industry_id, opened, closed) for region, (opened, closed) in sorted(acc.items())]

    def _gaps(self, anchor: date) -> dict[str, tuple[int, int]]:
        """담배권 빈자리 재료 (설계서 §6-1) — 후보 = 기준일 영업 상가(업종 무관), 소매인 = 기준일 영업 담배소매인(편의점 여부 무관)."""
        retailers = [
            GeoPoint(row.region_code, row.lat, row.lng)
            for row, record in zip(self._rows, self._records)
            if row.lat is not None and row.lng is not None
            and record.open_date is not None and _active(record.open_date, record.close_date, anchor)
        ]
        with session_scope() as session:
            candidates = [
                GeoPoint(region, lat, lng)
                for region, lat, lng in session.execute(
                    select(StoreOrm.region_code, StoreOrm.lat, StoreOrm.lng).where(
                        StoreOrm.region_code.is_not(None), StoreOrm.lat.is_not(None), StoreOrm.lng.is_not(None),
                        StoreOrm.open_date <= anchor,
                        or_(StoreOrm.close_date.is_(None), StoreOrm.close_date > anchor),
                    )
                ).all()
            ]
        return blocked_counts(candidates, retailers, self._radius_m)
