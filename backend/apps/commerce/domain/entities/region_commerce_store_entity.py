from dataclasses import dataclass


@dataclass(frozen=True)
class RegionCommerceStore:
    """서울 상권분석서비스 점포(행정동×업종×분기) 1행.

    open_rate/close_rate의 원천 헤더는 '개업_율'/'폐업_률'로 표기가 비대칭이다. 오타가 아니라
    원천 그대로이므로 그 이름으로 읽는다 (설계서 §2).
    """

    adstrd_code: str  # 원천 행정동_코드 8자리
    service_industry_code: str  # 원천 서비스_업종_코드 CS1NNNNN
    year_quarter: str  # 원천 기준_년분기_코드 '20251'
    region_code: str | None  # 앞 8자리 일치 시 기입 — 미매칭 옛 행정동은 None
    store_count: int | None  # 점포_수
    similar_industry_store_count: int | None  # 유사_업종_점포_수
    open_rate: float | None  # 개업_율
    open_store_count: int | None  # 개업_점포_수
    close_rate: float | None  # 폐업_률
    close_store_count: int | None  # 폐업_점포_수
    franchise_store_count: int | None  # 프랜차이즈_점포_수
