from dataclasses import dataclass


@dataclass(frozen=True)
class RegionPopulationQuarter:
    """직장·상주인구 1구간 — 두 원천의 값 컬럼 21개가 한 글자도 다르지 않다 (설계서 §3-3).

    같은 개념(등록 기반 인구를 성·연령으로 센 것)의 두 인스턴스이므로 `population_type`으로만
    구분해 한 테이블에 둔다. 원본 1행이 21행으로 펼쳐진다: total 1 · gender 2 · age 6 ·
    gender_age 12. `gender`·`age`는 `gender_age`의 주변합이지만 원천이 주는 값을 그대로 보존한다.
    """

    adstrd_code: str
    year_quarter: str
    population_type: str  # worker | resident
    dim_type: str  # total / gender / age / gender_age
    dim_key: str  # all, male, 30, female_60_over ...
    region_code: str | None
    headcount: int | None
