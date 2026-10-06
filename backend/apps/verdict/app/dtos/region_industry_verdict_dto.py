"""verdict BC DTO — 응답용(판정·범주값·대안) + 게이트웨이 출력(집계·맥락·점포수·업종·동). 프레임워크 타입 없음."""

from dataclasses import dataclass
from datetime import date, datetime

from apps.verdict.domain.entities.region_industry_verdict_entity import BASIS_PERMIT


@dataclass(frozen=True)
class SignalResultDto:
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str
    band: str | None = None
    band_label: str | None = None


@dataclass(frozen=True)
class RegionIndustryVerdictDto:
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: tuple[SignalResultDto, ...]
    computed_at: datetime
    basis: str = BASIS_PERMIT
    weak_basis: bool = False  # 판정 근거가 약한 업종 — 비추천을 내지 않는다


@dataclass(frozen=True)
class VerdictValueDto:
    """단계구분도 응답 단위 — {region_code, value: verdict_code} (범주 계약)."""

    region_code: str
    value: str


@dataclass(frozen=True)
class StoreSignalStat:
    """store 원천 집계 (동×업종). 없는 조합은 인터랙터가 0으로 채운다 → 표본 가드가 unavailable로 만든다."""

    region_code: str
    industry_id: str
    start_store_count: int
    opened_12m: int
    closed_12m: int
    cohort_size: int
    cohort_survived: int
    closed_3y_count: int
    closed_3y_median_months: float | None
    # 담배권 빈자리 (편의점 원천만 채운다, 업종 특화 신호 설계서 §6) — 다른 원천은 0 → 가드가 unavailable로 만든다
    gap_candidates: int = 0
    gap_blocked: int = 0
    # 행정동 배분 아파트 매매 12개월 합 (부동산 원천만 채운다, 업종 특화 신호 설계서 §11)
    trade_12m: float | None = None


@dataclass(frozen=True)
class RegionContext:
    """동 단위 맥락 — 전 행정동 1행씩 (프로필이 없으면 None)."""

    region_code: str
    resident_total: int | None


@dataclass(frozen=True)
class LatestStoreCount:
    region_code: str
    industry_id: str
    store_count: int


@dataclass(frozen=True)
class JudgedIndustry:
    industry_id: str
    name: str


@dataclass(frozen=True)
class RegionInfo:
    """동 카탈로그 — 이름과 최신 분기 동네 유형(프로필이 없으면 None)."""

    region_code: str
    name: str
    neighborhood_type: str | None


@dataclass(frozen=True)
class AlternativeIndustryDto:
    industry_id: str
    industry_name: str
    verdict_code: str
    strong_count: int
    on_count: int


@dataclass(frozen=True)
class AlternativeRegionDto:
    region_code: str
    region_name: str
    verdict_code: str
    strong_count: int
    on_count: int


@dataclass(frozen=True)
class VerdictAlternativesDto:
    """대안 두 축 (설계서 §12) — industries는 동네 고정, regions는 업종 고정(같은 동네 유형 안에서)."""

    region_code: str
    industry_id: str
    neighborhood_type: str | None
    industries: tuple[AlternativeIndustryDto, ...]
    regions: tuple[AlternativeRegionDto, ...]


@dataclass(frozen=True)
class EntrantOutcome:
    """진입 코호트 결과 (동×업종) — as_of 이후 entry_days 안에 개업한 수와 그중 horizon_days 안에 폐업한 수."""

    region_code: str
    industry_id: str
    opened: int
    closed_within: int


@dataclass(frozen=True)
class BacktestBucketDto:
    industry_id: str | None  # None = 전체
    industry_name: str | None
    verdict_code: str
    pairs: int
    opened: int
    closed: int

    @property
    def rate(self) -> float | None:
        return None if self.opened == 0 else self.closed / self.opened


@dataclass(frozen=True)
class BacktestSignalBucketDto:
    industry_id: str | None  # None = 전체
    industry_name: str | None
    signal_key: str
    fired: bool  # on·strong = True, off = False (unavailable 제외)
    pairs: int
    opened: int
    closed: int

    @property
    def rate(self) -> float | None:
        return None if self.opened == 0 else self.closed / self.opened


@dataclass(frozen=True)
class BacktestGateDto:
    """재포함 게이트 결과 (업종 특화 신호 설계서 §8)."""

    industry_id: str
    industry_name: str | None
    basis: str
    passed: bool
    warn_lift: float | None
    warn_opened: int
    clear_opened: int
    warn_pairs: int
    clear_pairs: int
    reason: str


@dataclass(frozen=True)
class BacktestReportDto:
    as_of: date
    quarter_max: str
    year_max: int
    entry_days: int
    horizon_days: int
    buckets: tuple[BacktestBucketDto, ...]
    signal_buckets: tuple[BacktestSignalBucketDto, ...]
    industry_basis: tuple[tuple[str, str], ...] = ()  # (industry_id, basis) — 표의 † 표기·심사 절 원천 칸
    gates: tuple[BacktestGateDto, ...] = ()
