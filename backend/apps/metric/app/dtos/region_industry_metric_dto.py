from dataclasses import dataclass


@dataclass
class RegionIndustryMetricDto:
    region_code: str
    industry_id: str
    year: int
    store_count: int
    open_count: int | None
    close_count: int | None
    closure_rate: float | None
    growth_rate: float | None


@dataclass
class MetricValueDto:
    """단계구분도 응답 단위 — {region_code, value} (프론트엔드 계약)."""

    region_code: str
    value: float


@dataclass(frozen=True)
class YearlyStoreStat:
    """집계 입력 단위 = 행정동×업종×연도의 store 원천 카운트."""

    region_code: str
    industry_id: str
    year: int
    store_count: int  # 연도 말 기준 영업 중 점포 수
    open_count: int  # 당해 개업 수
    close_count: int  # 당해 폐업 수


@dataclass(frozen=True)
class SnapshotStoreCount:
    """개폐업 이력 없는 스냅샷 원천(어린이집·편의점)의 행정동×업종 현행 점포수.

    year = 최신 관측일의 연도 — 스냅샷은 과거 연도를 복원할 수 없어 관측 연도에만 적재한다.
    """

    region_code: str
    industry_id: str
    year: int
    store_count: int
