from dataclasses import dataclass


@dataclass(frozen=True)
class RegionIndustryHourGap:
    """행정동×업종×분기×시간구간 — 사람이 몰리는 시간과 돈이 도는 시간의 차이.

    코사인 유사도 같은 단일 점수로 뭉개지 않는다. "사람은 출근길에 가장 많은데 돈은 오후에
    쓴다"를 말하려면 **어느 구간에서** 어긋나는지가 필요하다 (설계서 §4-2).

    두 강도 모두 시간당 보정을 거친 값이다. 구간 길이가 6·5·3·3·4·3시간으로 달라 원값끼리
    빼면 부호가 통째로 뒤집힌다.
    """

    region_code: str
    industry_id: str
    year_quarter: str
    hour_band: str  # 00_06 | 06_11 | 11_14 | 14_17 | 17_21 | 21_24
    footfall_intensity: float
    sales_intensity: float
    gap: float  # sales_intensity − footfall_intensity
