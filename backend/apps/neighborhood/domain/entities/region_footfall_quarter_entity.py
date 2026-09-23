from dataclasses import dataclass


@dataclass(frozen=True)
class RegionFootfallQuarter:
    """유동인구 1구간 — 원천 wide 25컬럼을 1NF long으로 편 한 행 (설계서 §4-1).

    원본 1행(행정동×분기)이 22행으로 펼쳐진다: total 1 · gender 2 · age 6 · hour 6 · dow 7.
    성별×연령 교차가 없고 시간대·요일이 있다 — 흐름(flow)을 센 데이터라 등록 상태(stock)인
    직장·상주인구와 축이 다르다. 그래서 같은 테이블에 합치지 않는다(설계서 §3-4).
    """

    adstrd_code: str  # 원천 행정동_코드 8자리
    year_quarter: str  # 원천 기준_년분기_코드 '20251' — 정수 변환 금지
    dim_type: str  # total / gender / age / hour / dow
    dim_key: str  # all, male, 30, 00_06, mon ...
    region_code: str | None  # 앞 8자리 일치 시 기입 — 원천에만 있는 옛 행정동 3개는 None
    headcount: int | None  # 사람 수 — 원천 공란은 0이 아니라 None
