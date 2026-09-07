"""시드 파일 검증 — 출처 필수·계층 유효·업종 연결 무결성·핵심 행 실값 (네트워크·DB 미사용)."""

from datetime import date

from apps.shock.adapter.outbound.gateways.shock_seed_gateway import ShockSeedGateway
from apps.shock.domain.value_objects.shock_layer import ShockLayer

# master 시드와 동일한 업종 10종 (apps/master seed_master)
_INDUSTRY_IDS = {
    "cafe", "convenience_store", "hair_salon", "karaoke", "pc_bang",
    "gym", "billiard", "real_estate", "academy", "childcare",
}


def _events():
    return ShockSeedGateway().fetch_events()


def test_every_seed_row_has_source_and_valid_layer():
    events = _events()
    assert events
    for event in events:
        assert event.source  # 출처 명시 — 과업 요구사항
        assert event.layer in ShockLayer
        for impact in event.industry_impacts:
            assert impact.industry_id in _INDUSTRY_IDS  # 조인 무결성 (industry FK 대상)


def test_seed_covers_pre_api_distancing_gap():
    """API 커버리지(2020-12-08~) 이전 1차 거리두기 구간을 시드가 보충한다."""
    events = _events()
    starts = {e.start_date for e in events}
    assert date(2020, 3, 22) in starts  # 강력한 사회적 거리두기 시작
    pre_api = [
        e for e in events
        if e.event_id.startswith("covid-") and e.start_date < date(2020, 12, 8)
    ]
    # 2020-03-22 ~ 2020-12-07 연속 커버 (구간 간 공백 없음)
    pre_api.sort(key=lambda e: e.start_date)
    for prev, nxt in zip(pre_api, pre_api[1:]):
        assert prev.end_date is not None
        assert (nxt.start_date - prev.end_date).days == 1
    assert pre_api[-1].end_date == date(2020, 12, 7)  # API 시작 전날까지


def test_minimum_wage_rows_2019_to_2026_with_real_amounts():
    by_id = {e.event_id: e for e in _events()}
    for year in range(2019, 2027):
        assert f"min-wage-{year}" in by_id
    assert "8,350" in by_id["min-wage-2019"].name
    assert "10,320" in by_id["min-wage-2026"].name
    assert by_id["min-wage-2026"].start_date == date(2026, 1, 1)


def test_relief_fund_rows_carry_distortion_warning():
    """지원금 왜곡 주의(§5.2 ⚠️)를 description에 담아 후속 분석이 참조한다."""
    events = [e for e in _events() if "지원금" in e.name or "손실보상" in e.name]
    assert events
    for event in events:
        assert "지연" in (event.description or "")
        assert len(event.industry_impacts) == len(_INDUSTRY_IDS)  # 전 업종 연결
