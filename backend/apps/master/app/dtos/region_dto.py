from dataclasses import dataclass


@dataclass
class RegionDto:
    region_code: str
    name: str


@dataclass
class RegionMetricSnapshot:
    """최신 연도 지표 스냅샷 — metric BC 응답의 ACL 통과형 (어댑터가 변환해 전달)."""

    store_count: int
    closure_rate: float | None
    growth_rate: float | None


@dataclass
class SummaryCardDto:
    label: str
    value: str
    grade: str  # fact(집계 수치) / signal(정성 신호) — 프론트엔드 신뢰 배지 계약


@dataclass
class RegionSummaryDto:
    region_code: str
    name: str
    industry_id: str
    cards: list[SummaryCardDto]
