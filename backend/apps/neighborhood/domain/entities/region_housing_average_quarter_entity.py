from dataclasses import dataclass


@dataclass(frozen=True)
class RegionHousingAverageQuarter:
    """아파트 평균 면적·시가 (설계서 §4-3 미확정 1 — 별도 테이블로 확정).

    세대 수(정수 개수)와 평균 면적(㎡ 실수)·평균 시가(원)를 한 값 컬럼에 섞으면 의미가 섞인다.
    단위가 다른 측정치이므로 컬럼을 나눠 별도 테이블로 둔다.
    """

    adstrd_code: str
    year_quarter: str
    region_code: str | None
    avg_area_m2: float | None  # 원천 아파트_평균_면적
    avg_price: int | None  # 원천 아파트_평균_시가 (원)
