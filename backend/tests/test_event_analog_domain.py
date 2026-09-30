"""유사 사례 분석 도메인 — 분기·변동폭·질문 유형 힌트·유사 사례 고르기 (순수 함수, DB 없음)."""

from datetime import date

import pytest

from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.services.event_analog import (
    EventImpact,
    IndustryMove,
    QuarterImpact,
    category_outlook,
    event_impact,
    is_current,
    quarter_impact,
    select_analogs,
    trend_counts,
    weak_streak,
)
from apps.shock.domain.services.event_category_hints import categories_in
from apps.shock.domain.services.event_window import Quarter, Window, event_quarters
from apps.shock.domain.services.industry_flows import IndustryFlows, WindowChange
from apps.shock.domain.value_objects.event_category import CATEGORY_YEARS, EventCategory

TODAY = date(2026, 9, 30)


def _event(event_id: str, start: date, category: str | None, end: date | None = None) -> ShockEvent:
    return ShockEvent(
        event_id=event_id,
        layer="policy",
        name=event_id,
        start_date=start,
        end_date=end,
        scope="전국",
        source="테스트 출처",
        category=category,
    )


def _flat(industry_id: str, opens: int, closes: int, stock: int = 1000) -> IndustryFlows:
    """2013-01부터 매달 같은 개폐업 — 시작 재고는 2012-12 한 달에 몰아 넣는다."""
    openings = {date(2012, 12, 1): stock}
    closings: dict[date, int] = {}
    for year in range(2013, 2027):
        for month in range(1, 13):
            openings[date(year, month, 1)] = opens
            closings[date(year, month, 1)] = closes
    return IndustryFlows(industry_id, industry_id, openings, closings)


def _quarter(index: int = 0, start: date = date(2020, 1, 1)) -> Quarter:
    return Quarter(index, Window(start, 3))


# ── 분기 ───────────────────────────────────────────────────────────────


def test_3년이_지난_이벤트는_이벤트_달부터_3개월씩_12분기를_본다():
    quarters = event_quarters(date(2020, 1, 20), TODAY, years=3)
    assert len(quarters) == 12
    assert quarters[0].window == Window(date(2020, 1, 1), 3)
    assert quarters[3].window == Window(date(2020, 10, 1), 3)  # 1년 차 마지막 3개월
    assert quarters[11].window == Window(date(2022, 10, 1), 3)


def test_분기는_달력이_아니라_이벤트가_시작된_달_기준이다():
    quarters = event_quarters(date(2015, 5, 20), TODAY, years=1)
    assert [q.window.start for q in quarters] == [
        date(2015, 5, 1), date(2015, 8, 1), date(2015, 11, 1), date(2016, 2, 1),
    ]


def test_분기의_연차와_번호와_기준_창():
    quarter = _quarter(5, date(2021, 4, 1))  # 2년 차 2분기
    assert (quarter.year, quarter.number) == (2, 2)
    # 기준은 이벤트 직전 1년의 같은 분기 — 2년 차면 24개월 전
    assert quarter.baseline == Window(date(2019, 4, 1), 3)
    assert _quarter(0).baseline == Window(date(2019, 1, 1), 3)


def test_끝나지_않은_분기는_보지_않는다():
    quarters = event_quarters(date(2026, 1, 1), TODAY, years=3)
    # 1~3월·4~6월만 완결, 7~9월은 9월이 아직 안 끝났다
    assert [q.window.start for q in quarters] == [date(2026, 1, 1), date(2026, 4, 1)]


def test_끝난_분기가_없으면_빈_목록이다():
    assert event_quarters(date(2026, 8, 3), TODAY, years=3) == []


@pytest.mark.parametrize("years", [0, 4])
def test_연수는_1에서_3_사이만_허용한다(years):
    with pytest.raises(ValueError):
        event_quarters(date(2020, 1, 20), TODAY, years=years)


# ── 변동폭 ─────────────────────────────────────────────────────────────


def test_창의_변동폭은_기준_창_대비_점포수_증감률과_개폐업_증감률이다():
    flows = _flat("cafe", opens=10, closes=5)
    flows.openings[date(2020, 2, 1)] = 30  # 창 안의 한 달만 개업 급증
    window = Window(date(2020, 1, 1), 3)
    change = flows.change(window, window.shifted(-12))
    assert change.openings == 50
    assert change.closings == 15
    assert change.openings_yoy_pct == pytest.approx(66.7)  # 50 vs 30
    assert change.closings_yoy_pct == 0.0
    base_stock = 1000 + (10 - 5) * 7 * 12  # 2013-01~2019-12
    assert change.stock_change_pct == pytest.approx(round(35 / base_stock * 100, 1))
    # 기준 3개월은 순증 15 → 초과 증감은 두 증감률의 차
    last_year = round(15 / (base_stock - 15 * 4) * 100, 1)
    assert change.excess_pct == pytest.approx(change.stock_change_pct - last_year, abs=0.1)


def test_비교_기준이_0이면_증감률은_없다():
    flows = IndustryFlows("gym", "헬스장", {date(2020, 1, 1): 3}, {})
    window = Window(date(2020, 1, 1), 1)
    change = flows.change(window, window.shifted(-12))
    assert change.openings == 3
    assert change.openings_yoy_pct is None
    assert change.stock_change_pct is None


def test_2년_차_분기는_이벤트_직전_1년과_견준다():
    flows = _flat("cafe", opens=10, closes=5)
    for month in range(1, 13):  # 1년 차 내내 개업 급증 — 2년 차 기준에 섞이면 안 된다
        flows.openings[date(2020, month, 1)] = 40
    impact = quarter_impact(_quarter(4, date(2021, 1, 1)), [flows], "cafe")
    # 2021년 1분기는 평소대로 순증 15 — 2019년 1분기와 같다. 점포수가 커진 만큼 증감률만 조금 낮다
    # (15/1840 − 15/1360). 12개월 전(2020년 1분기, 순증 105)과 견줬다면 −6%p 넘게 나온다
    assert impact.target is not None
    assert impact.target.change.excess_pct == pytest.approx(-0.3, abs=0.05)


# ── 강세·약세 업종 ──────────────────────────────────────────────────────


def test_분기별로_평소보다_더_늘어난_업종과_더_줄어든_업종을_3개씩_고른다():
    flows = [_flat(f"i{k}", opens=10, closes=10) for k in range(8)]
    for k, flow in enumerate(flows):
        flow.openings[date(2020, 1, 1)] = 20 + (k - 4) * 5  # i0 가장 약세, i7 가장 강세
    impact = quarter_impact(_quarter(), flows, target_id="i4")
    assert [m.industry_id for m in impact.strongest] == ["i7", "i6", "i5"]
    assert [m.industry_id for m in impact.weakest] == ["i0", "i1", "i2"]
    assert impact.target is not None and impact.target.industry_id == "i4"
    assert set(impact.excess) == {f"i{k}" for k in range(8)}  # 업종별 흐름을 그릴 값


def test_점포가_너무_적은_업종은_순위에서_뺀다():
    flows = [_flat("big", 10, 10), _flat("tiny", 0, 0, stock=10)]
    impact = quarter_impact(_quarter(), flows, "tiny")
    assert [m.industry_id for m in impact.strongest] == ["big"]
    assert impact.target is not None and impact.target.industry_id == "tiny"  # 대상 업종은 그래도 보여준다


def test_대상_업종의_흐름이_없으면_target은_없다():
    impact = quarter_impact(_quarter(), [_flat("cafe", 10, 5)], "academy")
    assert impact.target is None


def test_강세와_약세는_겹치지_않는다():
    flows = [_flat(f"i{k}", 10 + k, 10) for k in range(4)]
    impact = quarter_impact(_quarter(), flows, "i0")
    strong = {m.industry_id for m in impact.strongest}
    weak = {m.industry_id for m in impact.weakest}
    assert not strong & weak


# ── 진행 중·유사 사례 ───────────────────────────────────────────────────


def test_유형마다_비교_기간이_다르다():
    # 해마다 바뀌는 최저임금·한 번 지급하는 지원금은 그 해 4분기, 드문 감염병·제도 변경은 3년 12분기
    assert CATEGORY_YEARS == {
        EventCategory.PANDEMIC: 3,
        EventCategory.MINIMUM_WAGE: 1,
        EventCategory.WORK_HOURS: 3,
        EventCategory.RELIEF: 1,
    }


def test_진행_중은_유형이_있고_유형의_비교_기간_안에서_시작해_아직_끝나지_않은_이벤트다():
    assert is_current(_event("w26", date(2026, 1, 1), "minimum_wage", date(2026, 12, 31)), TODAY)
    assert not is_current(_event("w25", date(2025, 1, 1), "minimum_wage", date(2025, 12, 31)), TODAY)
    assert not is_current(_event("w25-open", date(2025, 1, 1), "minimum_wage"), TODAY)  # 1년이 지났다
    assert is_current(_event("virus", date(2024, 7, 1), "pandemic"), TODAY)  # 감염병은 3년 안이면 진행 중
    assert is_current(_event("h", date(2024, 7, 1), "work_hours"), TODAY)
    assert not is_current(_event("h", date(2021, 7, 1), "work_hours"), TODAY)  # 상시 효과지만 오래됨
    assert not is_current(_event("x", date(2026, 3, 1), None), TODAY)  # 유형 없음
    assert not is_current(_event("f", date(2026, 12, 1), "relief"), TODAY)  # 아직 시작 전


def test_유사_사례는_요청_유형의_지난_이벤트를_최근순으로_유형당_3건까지_고른다():
    events = [
        _event("covid", date(2020, 1, 20), "pandemic", date(2022, 4, 17)),
        _event("mers", date(2015, 5, 20), "pandemic", date(2015, 12, 23)),
        *[
            _event(f"w{y}", date(y, 1, 1), "minimum_wage", date(y, 12, 31))
            for y in range(2019, 2027)
        ],
        _event("etc", date(2020, 5, 4), "relief", date(2020, 8, 31)),
    ]
    picked = select_analogs(events, ["pandemic", "minimum_wage"], TODAY)
    assert [e.event_id for e in picked] == ["covid", "mers", "w2025", "w2024", "w2023"]


def test_감염병_영향은_3년_12분기를_담고_지속_기간을_센다():
    covid = _event("covid", date(2020, 1, 20), "pandemic", date(2022, 4, 17))
    impact = event_impact(covid, [_flat("cafe", 10, 5)], "cafe", TODAY)
    assert impact.years == 3
    assert [q.quarter.index for q in impact.quarters] == list(range(12))
    assert impact.current is False
    assert impact.duration_months == 27  # 2020-01 → 2022-04
    assert len(impact.series("cafe")) == 12
    assert impact.series("academy") == [None] * 12


def test_최저임금_영향은_그_해_4분기만_담는다():
    event = _event("w23", date(2023, 1, 1), "minimum_wage", date(2023, 12, 31))
    impact = event_impact(event, [_flat("cafe", 10, 5)], "cafe", TODAY)
    assert impact.years == 1
    assert [q.quarter.window.start for q in impact.quarters] == [
        date(2023, 1, 1), date(2023, 4, 1), date(2023, 7, 1), date(2023, 10, 1),
    ]


def test_끝나지_않은_이벤트는_지속_기간이_없다():
    impact = event_impact(_event("h", date(2021, 7, 1), "work_hours"), [], "cafe", TODAY)
    assert impact.duration_months is None


# ── 유형별 전망 ────────────────────────────────────────────────────────


def _impact(duration: int | None, quarters: list[tuple[float | None, list[tuple[str, float]], list[tuple[str, float]]]]):
    """(대상 초과증감, 강세[(업종, 값)], 약세[(업종, 값)]) 분기 목록으로 EventImpact를 만든다."""
    change = lambda v: WindowChange(0, 0, None, None, None, v)  # noqa: E731
    move = lambda i, v: IndustryMove(i, i, change(v))  # noqa: E731
    return EventImpact(
        event=_event("e", date(2020, 1, 1), "pandemic"),
        current=False,
        years=3,
        duration_months=duration,
        quarters=[
            QuarterImpact(
                quarter=_quarter(index),
                target=None if target is None else move("cafe", target),
                strongest=[move(i, v) for i, v in strong],
                weakest=[move(i, v) for i, v in weak],
                excess={} if target is None else {"cafe": target},
            )
            for index, (target, strong, weak) in enumerate(quarters)
        ],
    )


def test_약세_강세_분기_수는_평소_대비_0_3퍼센트포인트_밖만_센다():
    assert trend_counts([-0.8, -0.3, -0.2, 0.0, 0.3, 1.2, None]) == (2, 2)


def test_첫_분기부터_연속으로_약세였던_분기_수를_센다():
    assert weak_streak([-1.0, -0.8, -0.1, 2.2, -0.9, -0.7]) == 2  # 메르스 때 카페 — 흩어진 약세는 세지 않는다
    assert weak_streak([-0.8] * 12) == 12
    assert weak_streak([0.4, -1.0]) == 0
    assert weak_streak([None, -1.0]) == 0
    assert weak_streak([]) == 0


def test_대상_업종이_사례_분기의_과반에서_평소보다_줄었으면_약세다():
    impacts = [
        _impact(27, [(-0.8, [("chinese", 0.8)], []), (-1.4, [("gym", 0.9)], [])]),
        _impact(7, [(-1.0, [("chinese", 0.5)], []), (2.2, [("western", 1.1)], [])]),
    ]
    outlook = category_outlook("pandemic", impacts, "cafe")
    assert outlook.target_trend == "weak"
    assert outlook.analog_count == 2
    assert outlook.typical_duration_months == 17  # 27·7의 중앙값


def test_한_분기만_크게_튀어도_과반_분기로_판단한다():
    # 평균은 −1.4%p로 약세처럼 보이지만 5분기 중 4분기가 강세
    quarters = [(0.4, [], []), (0.5, [], []), (-9.1, [], []), (0.6, [], []), (0.7, [], [])]
    assert category_outlook("pandemic", [_impact(None, quarters)], "cafe").target_trend == "strong"


def test_여러_사례_분기에서_반복해_강세였던_업종을_추천한다():
    impacts = [
        _impact(27, [(-0.8, [("chinese", 0.8), ("pub", 0.7), ("cafe", 0.1)], [("pc_bang", -0.6)]),
                     (-1.4, [("gym", 0.9), ("western", 0.4)], [("pc_bang", -1.5)])]),
        _impact(7, [(-1.0, [("chinese", 0.5), ("billiard", 0.2)], [("pub", -0.2)]),
                    (2.2, [("western", 1.1)], [("korean", -0.1)])]),
    ]
    outlook = category_outlook("pandemic", impacts, "cafe")
    # 두 번 강세: 양식(평균 0.75)·중식(0.65) → 한 번: 헬스장(0.9). 대상 업종(cafe)은 뺀다
    assert [i for i, _ in outlook.recommended] == ["western", "chinese", "gym"]
    assert [i for i, _ in outlook.avoid] == ["pc_bang", "korean"]
    # 호프는 강세 한 번·약세 한 번 — 어느 쪽에도 넣지 않는다
    assert "pub" not in {i for i, _ in outlook.recommended + outlook.avoid}


def test_증감이_평소와_비슷하거나_엇갈리면_혼조다():
    impacts = [_impact(None, [(0.1, [], []), (-0.5, [], []), (0.6, [], [])])]
    outlook = category_outlook("minimum_wage", impacts, "cafe")
    assert outlook.target_trend == "mixed"
    assert outlook.typical_duration_months is None


def test_대상_업종_변동이_없으면_판단하지_않는다():
    assert category_outlook("relief", [_impact(3, [(None, [], [])])], "cafe").target_trend == "unknown"


# ── 질문 유형 힌트 ─────────────────────────────────────────────────────


def test_질문에서_감염병_상황을_알아본다():
    assert categories_in("새 바이러스가 유행하는데 지금 카페 창업해도 될까?") == ["pandemic"]


def test_질문에서_여러_유형을_순서대로_알아본다():
    assert categories_in("거리두기에 최저임금까지 오르면 어때") == ["pandemic", "minimum_wage"]


def test_질문이_없거나_단서가_없으면_유형도_없다():
    assert categories_in(None) == []
    assert categories_in("역삼동 카페 괜찮아?") == []


def test_유형_값은_4종이다():
    assert {c.value for c in EventCategory} == {"pandemic", "minimum_wage", "work_hours", "relief"}
