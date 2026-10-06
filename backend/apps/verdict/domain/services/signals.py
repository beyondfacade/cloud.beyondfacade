"""신호 — Specification 패턴 (CLAUDE.md §5). 신호 하나 = 클래스 하나, 새 신호는 클래스 추가로 끝난다.
값·가드·나쁜 방향·근거 문장은 신호가 스스로 안다. 백분위 분포는 인터랙터가 업종별로 넘긴다 (설계서 §3).
signals()가 내는 개수는 "항상 5개"가 아니라 프로필(profiles.py)이 정한 개수·순서다 — 인허가 5 · 편의점 6 · 부동산 6."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, replace

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_UNAVAILABLE,
    SignalResult,
)
from apps.verdict.domain.services.risk_band import band_of
from apps.verdict.domain.services.thresholds import VerdictThresholds, level_of, percentile_rank
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M



@dataclass(frozen=True)
class SignalInput:
    """동×업종 하나의 신호 입력 — 게이트웨이 출력을 인터랙터가 합쳐 만든다."""

    region_code: str
    industry_id: str
    industry_name: str
    # store 집계 (StoreSignalStatsPort)
    start_store_count: int  # 12개월 전 시점 영업중
    opened_12m: int
    closed_12m: int
    cohort_size: int  # 3~4년 전 개업
    cohort_survived: int  # 그중 3년 생존
    closed_3y_count: int
    closed_3y_median_months: float | None
    # 동 맥락 (RegionContextPort)
    latest_store_count: int | None  # region_industry_metric 최신 연도
    resident_total: int | None  # region_profile_quarter 최신 분기
    # 담배권 빈자리 (편의점 원천) — 기본값 0이면 TobaccoGapSignal 가드가 unavailable로 만든다
    gap_candidates: int = 0
    gap_blocked: int = 0
    trade_12m: float | None = None  # 행정동 배분 아파트 매매 12개월 합 (부동산 원천)


def _top(percentile: float) -> int:
    """'나쁜 쪽에서 N번째쯤' 표기 — 백분위 65 → 35번째쯤. 0번째는 말이 안 되니 최소 1."""
    return max(1, round(100 - percentile))


_BAND_WORDS = {
    "very_bad": lambda s: f"매우 {s.bad_word} 편",
    "bad": lambda s: f"{s.bad_word} 편",
    "normal": lambda s: "보통",
    "good": lambda s: f"{s.good_word} 편",
    "very_good": lambda s: f"매우 {s.good_word} 편",
}


class Signal(ABC):
    key: str
    source: str
    measure: str  # 재는 것 — 등급 라벨 앞머리
    bad_word: str  # 나쁜 쪽 관형형 ("높은")
    good_word: str  # 좋은 쪽 관형형 ("낮은")

    def band_label(self, band: str) -> str:
        return f"{self.measure} {_BAND_WORDS[band](self)}"

    @abstractmethod
    def raw_value(self, i: SignalInput, t: VerdictThresholds) -> float | None:
        """신호 원값. 표본 가드 미달이면 None (→ unavailable)."""

    @abstractmethod
    def worse(self, value: float) -> float:
        """나쁜 방향이 커지도록 부호를 맞춘 값 — 백분위는 이 값으로 낸다."""

    @abstractmethod
    def evidence(self, i: SignalInput, value: float) -> str:
        """근거 한 문장 — 숫자와 비교 기준을 반드시 넣는다 (설계서 §3-4)."""

    @abstractmethod
    def unavailable_reason(self, i: SignalInput, t: VerdictThresholds) -> str:
        """미판정 사유 문장."""

    def evaluate(self, i: SignalInput, t: VerdictThresholds, distribution: Sequence[float]) -> SignalResult:
        value = self.raw_value(i, t)
        if value is None:
            return SignalResult(self.key, LEVEL_UNAVAILABLE, None, None, self.unavailable_reason(i, t), self.source)
        percentile = percentile_rank(self.worse(value), distribution)
        band = band_of(percentile, t)
        label = self.band_label(band)
        evidence = (
            f"{self.evidence(i, value)} — {label}"
            f"(서울 {i.industry_name} 동을 100곳으로 치면 {self.bad_word} 쪽에서 {_top(percentile)}번째쯤)"
        )
        return SignalResult(
            self.key, level_of(percentile, t), value, round(percentile, 1), evidence, self.source,
            band=band, band_label=label,
        )


class NetOutflowSignal(Signal):
    key = "net_outflow"
    source = "store"
    measure = "순유출"
    bad_word = "많은"
    good_word = "적은"

    def raw_value(self, i, t):
        if i.start_store_count < t.min_sample:
            return None
        return (i.closed_12m - i.opened_12m) / i.start_store_count

    def worse(self, value):
        return value

    def evidence(self, i, value):
        return (
            f"지난 12개월 폐업 {i.closed_12m}곳, 개업 {i.opened_12m}곳 "
            f"(순유출률 {value * 100:+.0f}%)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 12개월 전 영업 점포 {i.start_store_count}곳 ({t.min_sample}곳 미만)"


class SurvivalCliffSignal(Signal):
    key = "survival_cliff"
    source = "store"
    measure = "생존율"
    bad_word = "낮은"
    good_word = "높은"

    def raw_value(self, i, t):
        if i.cohort_size < t.min_sample:
            return None
        return i.cohort_survived / i.cohort_size

    def worse(self, value):
        return -value  # 낮을수록 나쁨

    def evidence(self, i, value):
        return (
            f"3년 전 개업한 {i.industry_name} {i.cohort_size}곳 중 {i.cohort_survived}곳만 남음 "
            f"(생존율 {value * 100:.0f}%)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 3년 전 개업 코호트 {i.cohort_size}곳 ({t.min_sample}곳 미만)"


class EarlyClosureSignal(Signal):
    key = "early_closure"
    source = "store"
    measure = "폐업 점포 영업 기간"
    bad_word = "짧은"
    good_word = "긴"

    def raw_value(self, i, t):
        if i.closed_3y_count < t.min_sample or i.closed_3y_median_months is None:
            return None
        return i.closed_3y_median_months

    def worse(self, value):
        return -value  # 짧을수록 나쁨

    def evidence(self, i, value):
        return f"최근 3년 폐업 {i.industry_name}의 영업 기간 중위 {value:.0f}개월"

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 최근 3년 폐업 {i.closed_3y_count}곳 ({t.min_sample}곳 미만)"


class SaturationSignal(Signal):
    key = "saturation"
    source = "metric"
    measure = "밀집"
    bad_word = "높은"
    good_word = "낮은"

    def raw_value(self, i, t):
        if i.resident_total is None or i.resident_total < t.min_population or i.latest_store_count is None:
            return None
        return i.latest_store_count / (i.resident_total / 1000)

    def worse(self, value):
        return value

    def evidence(self, i, value):
        return f"상주인구 1,000명당 {i.industry_name} {value:.1f}곳"

    def unavailable_reason(self, i, t):
        if i.latest_store_count is None:
            return "최신 연도 점포수 지표 없음"
        return f"상주인구 {i.resident_total or 0:,}명 ({t.min_population:,}명 미만이거나 프로필 없음)"


class ClosureRateSignal(Signal):
    """집계 원천 폐업률 — 개업 수가 끊긴 원천(부동산 아카이브 2024Q1~)에서 순유출 대신 쓴다 (업종 특화 신호 설계서 §7-1)."""

    key = "closure_rate"
    source = "commerce"
    measure = "폐업률"
    bad_word = "높은"
    good_word = "낮은"

    def raw_value(self, i, t):
        if i.start_store_count < t.min_sample:
            return None
        return i.closed_12m / i.start_store_count

    def worse(self, value):
        return value

    def evidence(self, i, value):
        return (
            f"지난 4분기 폐업 {i.closed_12m:,}곳 (4분기 전 점포 {i.start_store_count:,}곳의 {value * 100:.0f}%, "
            f"서울시 상권분석 집계)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 4분기 전 점포 {i.start_store_count}곳 ({t.min_sample}곳 미만)"


class TobaccoGapSignal(Signal):
    """담배권 빈자리 — 상가 자리 중 영업 중인 담배소매인 반경 안 비율, 높을수록 나쁨. 참고 신호 (설계서 §6)."""

    key = "tobacco_gap"
    source = "tobacco"
    measure = "담배소매인 반경 안 상가 비율"
    bad_word = "높은"
    good_word = "낮은"

    def raw_value(self, i, t):
        if i.gap_candidates < t.min_gap_candidates:
            return None
        return i.gap_blocked / i.gap_candidates

    def worse(self, value):
        return value

    def evidence(self, i, value):
        return (
            f"이 동 상가 자리 {i.gap_candidates:,}곳 중 {value * 100:.0f}%가 영업 중인 담배소매인 "
            f"{TOBACCO_GAP_RADIUS_M:.0f}m 안 — 새 담배소매인 지정이 어렵다"
        )

    def unavailable_reason(self, i, t):
        return f"상가 좌표 표본 부족 — {i.gap_candidates}곳 ({t.min_gap_candidates}곳 미만)"


class SourcedSignal(Signal):
    """Decorator — 같은 계산을 다른 원천 데이터로 돌릴 때 source 표기만 바꾼다 (업종 특화 신호 설계서 §4)."""

    def __init__(self, inner: Signal, source: str) -> None:
        self._inner = inner
        self.key = inner.key
        self.source = source

    def raw_value(self, i, t):
        return self._inner.raw_value(i, t)

    def worse(self, value):
        return self._inner.worse(value)

    def evidence(self, i, value):
        return self._inner.evidence(i, value)

    def unavailable_reason(self, i, t):
        return self._inner.unavailable_reason(i, t)

    def evaluate(self, i, t, distribution):
        return replace(self._inner.evaluate(i, t, distribution), source=self.source)


class UnsupportedSignal(Signal):
    """Null Object — 원천이 이 신호의 재료를 주지 않는다. 표본 부족과 다른 사유 문장으로 항상 unavailable (설계서 §7-1)."""

    def __init__(self, key: str, source: str, reason: str) -> None:
        self.key = key
        self.source = source
        self._reason = reason

    def raw_value(self, i, t):
        return None

    def worse(self, value):
        return value

    def evidence(self, i, value):
        return self._reason

    def unavailable_reason(self, i, t):
        return self._reason


class TradePerOfficeSignal(Signal):
    """중개사무소당 아파트 매매 — 낮을수록 나쁨. 법정동 배분이 근사라 참고 신호 (업종 특화 신호 설계서 §11)."""

    key = "trade_per_office"
    source = "molit"
    measure = "사무소당 거래"
    bad_word = "적은"
    good_word = "많은"

    def raw_value(self, i, t):
        if i.trade_12m is None or i.latest_store_count is None or i.latest_store_count < t.min_sample:
            return None
        return i.trade_12m / i.latest_store_count

    def worse(self, value):
        return -value

    def evidence(self, i, value):
        return (
            f"지난 12개월 아파트 매매 {i.trade_12m:,.0f}건 ÷ 중개사무소 {i.latest_store_count}곳 = 사무소당 {value:.1f}건 "
            f"(국토부 실거래가)"
        )

    def unavailable_reason(self, i, t):
        return f"실거래 배분 없음 또는 중개사무소 {t.min_sample}곳 미만"


SIGNALS: tuple[Signal, ...] = (
    NetOutflowSignal(),
    SurvivalCliffSignal(),
    EarlyClosureSignal(),
    SaturationSignal(),
)
