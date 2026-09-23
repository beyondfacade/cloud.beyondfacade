"""파생 지표 배치 러너 (Driving Adapter, CLI).

- 입력: neighborhood BC 동네 맥락 + commerce BC 매출 분해 — 외부 API 호출 없음
- 산출: region_profile_quarter (22분기) · region_industry_hour_gap_quarter (20분기) 업서트
- 분기 범위가 다른 이유: 동네 맥락은 20211~20262, 매출은 20211~20254다 (설계서 §3-5)

실행: python -m apps.metric.adapter.inbound.cli.build_region_profiles
"""

from apps.metric.dependencies.region_profile_dependencies import (
    get_region_industry_hour_gap_use_case,
    get_region_profile_use_case,
)


def _quarters(first: str, last: str) -> list[str]:
    quarters = []
    year, quarter = int(first[:4]), int(first[4])
    while f"{year}{quarter}" <= last:
        quarters.append(f"{year}{quarter}")
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
    return quarters


PROFILE_QUARTERS = _quarters("20211", "20262")
HOUR_GAP_QUARTERS = _quarters("20211", "20254")


def main() -> None:
    profiles = get_region_profile_use_case().build(PROFILE_QUARTERS)
    print(f"동네 프로필 업서트: {profiles}건 ({PROFILE_QUARTERS[0]}~{PROFILE_QUARTERS[-1]})")
    gaps = get_region_industry_hour_gap_use_case().build(HOUR_GAP_QUARTERS)
    print(f"시간대 어긋남 업서트: {gaps}건 ({HOUR_GAP_QUARTERS[0]}~{HOUR_GAP_QUARTERS[-1]})")


if __name__ == "__main__":
    main()
