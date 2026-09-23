from dataclasses import dataclass


@dataclass(frozen=True)
class RegionCommerceSales:
    """서울 상권분석서비스 추정매출(행정동×업종×분기) 1행 — 원천 코드를 원본 그대로 보존한다.

    year_quarter는 '20251'(2025년 1분기) 5자리 문자열이다. 정수로 바꾸면 2025와 구분되지
    않으므로 문자열로 둔다. 매출 분해 47컬럼은 이번 범위 밖 (설계서 §4-1).
    """

    adstrd_code: str  # 원천 행정동_코드 8자리
    service_industry_code: str  # 원천 서비스_업종_코드 CS1NNNNN
    year_quarter: str  # 원천 기준_년분기_코드 '20251'
    region_code: str | None  # 앞 8자리 일치 시 기입 — 옛 행정동 3개(용신·일원2·상일)는 None
    sales_amount: int | None  # 당월_매출_금액 — 결측은 0이 아니라 None 보존
    sales_count: int | None  # 당월_매출_건수
