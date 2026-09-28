"""verdict BC DTO — 응답용 3종 + 게이트웨이 출력 4종. 프레임워크 타입 없음."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SignalResultDto:
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str


@dataclass(frozen=True)
class RegionIndustryVerdictDto:
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: tuple[SignalResultDto, ...]
    computed_at: datetime


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


@dataclass(frozen=True)
class RegionContext:
    """동 단위 맥락 — 전 행정동 1행씩 (프로필·변화지표가 없으면 None)."""

    region_code: str
    resident_total: int | None
    change_code: str | None
    change_name: str | None
    change_quarter: str | None
    closed_months: float | None
    seoul_closed_months: float | None


@dataclass(frozen=True)
class LatestStoreCount:
    region_code: str
    industry_id: str
    store_count: int


@dataclass(frozen=True)
class JudgedIndustry:
    industry_id: str
    name: str
