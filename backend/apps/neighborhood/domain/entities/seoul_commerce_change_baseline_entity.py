from dataclasses import dataclass


@dataclass(frozen=True)
class SeoulCommerceChangeBaseline:
    """분기별 서울 전체 평균 — 2NF 분리 결과 (설계서 §3-5 · §4-7).

    원천 상권변화 데이터의 `서울_운영_영업_개월_평균`·`서울_폐업_영업_개월_평균`은 행정동이
    아니라 분기에만 의존한다(22개 분기 전부에서 고유값 1개 실측). 425개 동에 같은 값이 반복되는
    부분 함수 종속이므로 떼어낸다. `region_commerce_change.year_quarter`가 이 테이블을 참조해
    "고립된 테이블 금지"(§13)를 만족한다.
    """

    year_quarter: str
    seoul_operating_months: float | None
    seoul_closed_months: float | None
