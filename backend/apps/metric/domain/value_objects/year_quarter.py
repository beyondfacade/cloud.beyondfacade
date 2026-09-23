"""분기 문자열 어휘 — profile·hour_gap 두 프랙탈이 횡단 공유하는 VO.

원천 표기는 `'20211'`(연 4자리 + 분기 1자리)이다. 판정 창이 연도 경계를 넘어가므로 문자열
정렬만으로는 직전 분기를 구할 수 없다.
"""


def previous_quarter(year_quarter: str) -> str:
    year, quarter = int(year_quarter[:4]), int(year_quarter[4])
    if quarter == 1:
        return f"{year - 1}4"
    return f"{year}{quarter - 1}"


def quarter_window(year_quarter: str, size: int) -> list[str]:
    """해당 분기를 포함한 직전 `size`개 분기를 과거→현재 순으로 반환한다 (설계서 §5-2)."""
    window = [year_quarter]
    for _ in range(size - 1):
        window.append(previous_quarter(window[-1]))
    return list(reversed(window))
