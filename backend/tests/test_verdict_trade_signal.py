"""중개사무소당 거래 참고 신호 — 법정동 배분·월 창·Decorator·신호 값 (업종 특화 신호 설계서 §11)."""

from datetime import date

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort, TradeCountsPort
from apps.verdict.app.use_cases.industry_source import TradeEnrichedSignalData
from apps.verdict.domain.entities.region_industry_verdict_entity import ADVISORY_SIGNAL_KEYS, LEVEL_UNAVAILABLE
from apps.verdict.domain.services.legal_dong import allocate, legal_dong_of, month_window
from apps.verdict.domain.services.signals import SignalInput, TradePerOfficeSignal
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


@pytest.mark.parametrize("address, dong", [
    ("서울특별시 강남구 역삼동 123-4", "역삼동"),
    ("서울특별시 중구 을지로3가 5", "을지로3가"),
    ("서울시 종로구 종로1가 1", "종로1가"),
    ("경기도 성남시 분당구 정자동 1", None),
    (None, None),
])
def test_지번주소에서_법정동을_읽는다(address, dong):
    assert legal_dong_of(address) == dong


def test_법정동_건수를_상가_분포_비율로_행정동에_나눈다():
    trades = {("11680", "역삼동"): 100, ("11680", "없는동"): 7}
    weights = {("11680", "역삼동"): {"1168064000": 3, "1168065000": 1}}
    assert allocate(trades, weights) == {"1168064000": 75.0, "1168065000": 25.0}  # 배분 못 한 7건은 버린다


def test_월_창은_기준월_2개월_전까지_12개월이다():
    assert month_window(date(2026, 9, 29)) == ("202508", "202607")
    assert month_window(date(2022, 6, 30)) == ("202105", "202204")


class _Inner(IndustrySignalDataPort):
    def signal_stats(self, today):
        return [StoreSignalStat("r1", "real_estate", 100, 0, 5, 0, 0, 0, None)]

    def store_counts(self, year_max, quarter_max):
        return ["counts"]

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return ["outcomes"]


class _Trades(TradeCountsPort):
    def __init__(self):
        self.args = None

    def trades_by_region(self, month_from, month_to):
        self.args = (month_from, month_to)
        return {"r1": 240.0}


def test_거래_Decorator는_집계_원천에_12개월_거래를_얹고_나머지는_위임한다():
    trades = _Trades()
    data = TradeEnrichedSignalData(_Inner(), trades)
    (stat,) = data.signal_stats(date(2022, 6, 30))
    assert stat.trade_12m == 240.0 and trades.args == ("202105", "202204")
    assert data.store_counts(None, None) == ["counts"]
    assert data.entrant_outcomes(date(2022, 6, 30), 365, 1095) == ["outcomes"]


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="r1", industry_id="real_estate", industry_name="부동산중개업",
        start_store_count=100, opened_12m=0, closed_12m=5, cohort_size=0, cohort_survived=0,
        closed_3y_count=0, closed_3y_median_months=None, latest_store_count=80, resident_total=10_000,
        change_code="HH", change_name="정체", change_quarter="20262", closed_months=25.0, seoul_closed_months=27.0,
        trade_12m=240.0,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_사무소당_거래는_낮을수록_나쁘고_참고_신호다():
    signal = TradePerOfficeSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(3.0)
    assert signal.worse(3.0) == -3.0
    assert signal.evaluate(_input(trade_12m=None), T, [1.0]).level == LEVEL_UNAVAILABLE
    assert signal.evaluate(_input(latest_store_count=9), T, [1.0]).level == LEVEL_UNAVAILABLE
    assert "사무소당 3.0건" in signal.evaluate(_input(), T, [-5.0, -1.0]).evidence
    assert "trade_per_office" in ADVISORY_SIGNAL_KEYS
