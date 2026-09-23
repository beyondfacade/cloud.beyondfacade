from dataclasses import dataclass


@dataclass(frozen=True)
class RegionHouseholdQuarter:
    """가구·아파트 스톡 1구간 — 상주인구의 가구 3종과 아파트 데이터셋을 합친다 (설계서 §4-3).

    가구 수는 인구가 아니라 주거 스톡이라 `region_population_quarter`가 아니라 이쪽에 둔다.
    아파트 평균 면적·시가는 단위가 세대 수가 아니므로 같은 `value` 컬럼에 담지 않고
    `region_housing_average_quarter`로 뺀다.
    """

    adstrd_code: str
    year_quarter: str
    dim_type: str  # household / apartment_complex / apartment_area / apartment_price
    dim_key: str  # total, apartment, non_apartment, count, under_66, 100m ...
    region_code: str | None
    value: int | None  # 세대 수 또는 단지 수 — 원천 공란은 None
