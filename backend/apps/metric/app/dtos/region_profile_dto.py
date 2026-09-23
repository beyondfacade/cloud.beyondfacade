from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class RegionProfileDto:
    region_code: str
    year_quarter: str
    neighborhood_type: str
    type_reason: str
    time_label: str | None
    peak_block: str | None
    trough_block: str | None
    worker_resident_ratio: float | None
    weekend_index: float | None
    night_index: float | None
    footfall_20s_share: float | None
    fnb_share: float | None
    facility_total: int | None
    resident_total: int | None


@dataclass(frozen=True)
class RegionQuarterObservation:
    """판정 입력 단위 = 행정동×분기의 동네 맥락 원자료 한 묶음.

    `worker_total`이 None인 것은 "직장인구 0명"이 아니라 **원천에 그 동이 없다**는 뜻이다
    (11개 동). 0으로 채우면 주거형으로 오판한다 (설계서 §3-4).
    """

    region_code: str
    year_quarter: str
    worker_total: int | None
    resident_total: int | None
    footfall_by_hour: Mapping[str, float] = field(default_factory=dict)
    footfall_by_dow: Mapping[str, float] = field(default_factory=dict)
    footfall_20s: float | None = None
    footfall_age_total: float | None = None
    spending_total: int | None = None
    spending_fnb: int | None = None  # 음식 + 유흥
    facility_total: int | None = None
    university_count: int | None = None
