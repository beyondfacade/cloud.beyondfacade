"""유사 사례 계산 범위 — 내 업종은 자치구 점포가 충분하면 그 구, 모자라면 서울 전체 (DB 없음)."""

from datetime import date

from apps.shock.domain.services.analog_scope import (
    DISTRICT_MIN_STOCK,
    SCOPE_DISTRICT,
    SCOPE_SEOUL,
    SEOUL_NAME,
    choose_scope,
)
from apps.shock.domain.services.industry_flows import IndustryFlows

_MONTH = date(2026, 9, 1)


def _flows(industry_id: str, stock: int) -> IndustryFlows:
    return IndustryFlows(industry_id, industry_id, {date(2020, 1, 1): stock}, {})


def test_구의_내_업종_점포가_기준_이상이면_구로_계산한다():
    scope = choose_scope(
        [_flows("cafe", 60_000)], [_flows("cafe", DISTRICT_MIN_STOCK), _flows("pub", 10)],
        "cafe", "관악구", _MONTH,
    )
    assert (scope.level, scope.name, scope.target_stock) == (SCOPE_DISTRICT, "관악구", DISTRICT_MIN_STOCK)
    assert scope.comparison_name == SEOUL_NAME
    assert scope.min_stock == DISTRICT_MIN_STOCK


def test_구의_내_업종_점포가_기준에_못_미치면_서울_전체로_계산한다():
    scope = choose_scope(
        [_flows("billiard", 2_600)], [_flows("billiard", DISTRICT_MIN_STOCK - 1)], "billiard", "관악구", _MONTH
    )
    assert (scope.level, scope.name, scope.target_stock) == (SCOPE_SEOUL, SEOUL_NAME, 2_600)


def test_구를_모르거나_구에_그_업종이_없으면_서울_전체로_계산한다():
    seoul = [_flows("cafe", 60_000)]
    assert choose_scope(seoul, [], "cafe", None, _MONTH).level == SCOPE_SEOUL
    assert choose_scope(seoul, [_flows("pub", 5_000)], "cafe", "관악구", _MONTH).level == SCOPE_SEOUL


def test_서울에도_그_업종이_없으면_점포_수는_0이다():
    assert choose_scope([], [], "academy", None, _MONTH).target_stock == 0
