"""업종별 판정 원천 — 신호 프로필(도메인 Strategy)과 데이터 포트를 한 쌍으로 묶는다 (업종 특화 신호 설계서 §4)."""

from dataclasses import dataclass, replace
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    EntrantOutcomePort,
    IndustrySignalDataPort,
    RegionContextPort,
    StoreSignalStatsPort,
    TradeCountsPort,
)
from apps.verdict.domain.services.legal_dong import month_window
from apps.verdict.domain.services.profiles import SignalProfile


@dataclass(frozen=True, eq=False)  # 원천 객체 동일성으로 해시 — 인터랙터가 원천마다 한 번만 읽는 캐시 키
class IndustrySource:
    profile: SignalProfile
    data: IndustrySignalDataPort


class PermitSignalData(IndustrySignalDataPort):
    """Adapter — 기존 인허가 포트 3개를 원천 포트 하나로 묶는다(등록 안 된 업종의 기본 원천)."""

    def __init__(
        self, store_stats: StoreSignalStatsPort, region_context: RegionContextPort, entrant_outcomes: EntrantOutcomePort
    ) -> None:
        self._store_stats = store_stats
        self._region_context = region_context
        self._entrant_outcomes = entrant_outcomes

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        return self._store_stats.signal_stats(today)

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        return self._region_context.latest_store_counts(year_max)  # 연말 스냅샷 원천이라 연도 상한만 본다

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        return self._entrant_outcomes.entrant_outcomes(as_of, entry_days, horizon_days)


class TradeEnrichedSignalData(IndustrySignalDataPort):
    """Decorator — 원천 집계에 행정동 배분 아파트 매매 12개월 합(trade_12m)을 얹는다. 나머지는 위임 (설계서 §11)."""

    def __init__(self, inner: IndustrySignalDataPort, trades: TradeCountsPort) -> None:
        self._inner = inner
        self._trades = trades

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        by_region = self._trades.trades_by_region(*month_window(today))
        return [replace(s, trade_12m=by_region.get(s.region_code)) for s in self._inner.signal_stats(today)]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        return self._inner.store_counts(year_max, quarter_max)

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        return self._inner.entrant_outcomes(as_of, entry_days, horizon_days)
