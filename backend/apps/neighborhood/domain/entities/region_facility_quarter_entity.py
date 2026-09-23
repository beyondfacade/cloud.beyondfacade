from dataclasses import dataclass


@dataclass(frozen=True)
class RegionFacilityQuarter:
    """집객시설 1종 — 원천 wide 23컬럼을 1NF long으로 편 한 행 (설계서 §4-4).

    원본 1행이 20행으로 펼쳐진다: `total`(원천 집객시설_수) + 19종. 19종 합이 total과 맞는지는
    적재 후 SQL로 검증한다 — 원천이 보장하지 않는다.
    """

    adstrd_code: str
    year_quarter: str
    facility_type: str  # total + government, bank, subway_station ... 19종
    region_code: str | None
    facility_count: int | None  # 원천 공란은 0이 아니라 None (집객시설 원천에 공란이 흔하다)
