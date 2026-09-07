from dataclasses import dataclass


@dataclass(frozen=True)
class InterestRate:
    """금리 시계열 1점 — 계산기·부동산 분석 공용 독립 시계열 (docs/erd.md §4 역정규화 근거).

    MVP는 한국은행 기준금리(rate_type="base")만. 가중평균 대출금리(121Y006) 확장 대비
    rate_type·stat_code·item_code를 보존한다.
    """

    id: str  # "{rate_type}:{period}"
    rate_type: str  # "base" — 한국은행 기준금리
    period: str  # YYYYMM
    rate: float
    unit: str  # "연%"
    stat_code: str  # ECOS 통계코드 (722Y001)
    item_code: str  # ECOS 항목코드 (0101000)
