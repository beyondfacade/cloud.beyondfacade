from dataclasses import dataclass


@dataclass(frozen=True)
class RegionCommerceSalesBreakdown:
    """추정매출 분해 1구간 — 원천 wide 47컬럼을 1NF long으로 편 한 행 (설계서 §4-1).

    원본 1행(행정동×업종×분기)이 23개 구간 행으로 펼쳐진다. 금액과 건수를 한 행에 같이 두는
    근거: 두 값이 같은 구간의 두 측정치라 (dim_type, dim_key)가 동일한 키를 공유한다.
    금액만/건수만 별도 행으로 쪼개면 같은 구간을 두 번 저장하게 된다.
    """

    adstrd_code: str  # 원천 행정동_코드 8자리
    service_industry_code: str  # 원천 서비스_업종_코드 CS1NNNNN
    year_quarter: str  # 원천 기준_년분기_코드 '20251'
    dim_type: str  # 분해 축 — weekpart / dow / hour / gender / age
    dim_key: str  # 축 안의 구간 — weekday, mon, 00_06, male, 60_over ...
    region_code: str | None  # 앞 8자리 일치 시 기입 — 옛 행정동 3개는 None
    amount: int | None  # 해당 구간 매출 금액 — 원천 공란은 0이 아니라 None
    count: int | None  # 해당 구간 매출 건수
