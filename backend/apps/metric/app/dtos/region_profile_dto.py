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


@dataclass
class ProfileMetricValueDto:
    """단계구분도 응답 단위 — {region_code, value}.

    `/metrics`·`/commerce-changes`와 같은 계약이다 (설계서 `map-metric-contract` §3-1).
    """

    region_code: str
    value: float


@dataclass
class ProfileTypeDto:
    """유형 단계구분도 응답 단위 — {region_code, type_code}.

    숫자 계약(`{region_code, value}`)과 **경로를 나눈다**(`map-metric-contract` §5). 한 객체에
    value/category를 두고 한쪽을 null로 두면 타입이 거짓말한다.
    """

    region_code: str
    type_code: str  # office | campus | dining | hub | residential | mixed


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
