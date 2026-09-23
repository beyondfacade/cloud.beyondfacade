from dataclasses import dataclass


@dataclass(frozen=True)
class RegionSpendingQuarter:
    """지출 1항목 — 원천 wide 14컬럼을 1NF long으로 편 한 행 (설계서 §4-5).

    원본 1행이 11행으로 펼쳐진다: `total`(지출_총금액) + 10종. **원천 컬럼 순서에서 `음식`이
    `기타` 뒤에 온다** — 순서로 매핑하면 두 항목이 통째로 뒤바뀐다(설계서 §3-7).
    """

    adstrd_code: str
    year_quarter: str
    spending_category: str  # total + grocery, clothing_shoes ... food
    region_code: str | None
    amount: int | None  # 지출 금액(원) — 원천 공란은 None
