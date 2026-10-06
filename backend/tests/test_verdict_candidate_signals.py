"""백테스트 전용 후보 신호 — 원값 가드·업종 안 백분위 켜짐·켜짐/꺼짐 집계·T 간 안정성 (실험 브랜치, 운영 판정 무관)."""

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome
from apps.verdict.domain.services.candidate_signals import (
    fired_flags,
    opening_rush,
    sales_trend,
    saturation_demand,
    stable_hits,
    summarize_candidate,
)


def test_수요_포화는_점포수를_수요_천명당으로_나누고_가드_미달이면_None이다():
    assert saturation_demand(30, 20_000, min_demand=1000) == 1.5
    assert saturation_demand(30, 999, min_demand=1000) is None
    assert saturation_demand(None, 20_000, min_demand=1000) is None
    assert saturation_demand(30, None, min_demand=1000) is None


def test_개업_러시는_12개월_개업을_12개월_전_점포수로_나누고_표본_가드를_둔다():
    assert opening_rush(opened_12m=5, start_store_count=20, min_sample=10) == 0.25
    assert opening_rush(opened_12m=5, start_store_count=9, min_sample=10) is None


def test_매출_추세는_점포당_매출의_전년_동분기_대비_변화율이다():
    # 점포당 100 → 80 = −20%
    assert sales_trend(sales_now=1600, stores_now=20, sales_prev=1000, stores_prev=10, min_sample=10) == pytest.approx(-0.2)
    assert sales_trend(sales_now=1600, stores_now=20, sales_prev=1000, stores_prev=9, min_sample=10) is None
    assert sales_trend(sales_now=1600, stores_now=20, sales_prev=0, stores_prev=10, min_sample=10) is None
    assert sales_trend(sales_now=None, stores_now=20, sales_prev=1000, stores_prev=10, min_sample=10) is None


def test_켜짐은_업종_안_백분위로_정하고_가드_미달은_빠진다():
    values = {(f"r{n}", "cafe"): float(n) for n in range(4)} | {("r0", "pub"): 9.0, ("r9", "cafe"): None}
    fired = fired_flags(values, worse=lambda v: v, on_percentile=75.0)
    assert fired == {("r0", "cafe"): False, ("r1", "cafe"): False, ("r2", "cafe"): False, ("r3", "cafe"): True,
                     ("r0", "pub"): False}


def test_나쁜_방향이_음수면_가장_낮은_값이_켜진다():
    values = {(f"r{n}", "cafe"): float(n) for n in range(4)}
    fired = fired_flags(values, worse=lambda v: -v, on_percentile=75.0)
    assert [k for k, on in fired.items() if on] == [("r0", "cafe")]


def test_후보_신호_집계는_전체와_업종별_켜짐_꺼짐_버킷을_낸다():
    fired = {("r1", "cafe"): True, ("r2", "cafe"): False, ("r1", "pub"): False}
    outcomes = [EntrantOutcome("r1", "cafe", 10, 6), EntrantOutcome("r2", "cafe", 10, 3), EntrantOutcome("r1", "pub", 4, 1)]
    cells = {(b.industry_id, b.fired): (b.opened, b.closed) for b in summarize_candidate("opening_rush", fired, outcomes)}
    assert cells == {(None, True): (10, 6), (None, False): (14, 4), ("cafe", True): (10, 6), ("cafe", False): (10, 3),
                     ("pub", False): (4, 1)}


def test_안정성은_표본이_충분한_T_중_lift_기준을_넘은_수를_센다():
    # (lift, 켜짐 개업, 꺼짐 개업) — 두 번째는 lift가 낮고, 세 번째는 표본 부족, 네 번째는 계산 불가
    cells = [(1.30, 120, 900), (1.05, 200, 900), (1.50, 30, 900), None]
    assert stable_hits(cells, min_lift=1.10, min_opened=50) == (1, 2)
