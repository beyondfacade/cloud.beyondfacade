"""백테스트 CLI 렌더 — 재포함 심사 절·원천 표기·† (업종 특화 신호 설계서 §7-3·§8)."""

from datetime import date

from apps.verdict.adapter.inbound.cli.backtest_verdicts import _missing_industry_ids, render_markdown
from apps.verdict.app.dtos.region_industry_verdict_dto import BacktestBucketDto, BacktestGateDto, BacktestReportDto


def _report(industry, name, basis, gates=()):
    buckets = (
        BacktestBucketDto(industry, name, "orange", 100, 400, 80),
        BacktestBucketDto(industry, name, "clear", 80, 200, 30),
    )
    return BacktestReportDto(
        as_of=date(2022, 6, 30), quarter_max="20221", year_max=2021, entry_days=365, horizon_days=1095,
        buckets=buckets, signal_buckets=(), industry_basis=((industry, basis),), gates=gates,
    )


def test_심사_절은_원천과_경고_lift와_게이트_결과를_찍는다():
    gate = BacktestGateDto("convenience_store", "편의점", "proxy", True, 1.4, 400, 200, 100, 80, "통과")
    text = render_markdown(
        _report("korean_food", "한식", "permit"), date(2026, 9, 29), _report("convenience_store", "편의점", "proxy", (gate,))
    )
    assert "## 재포함 심사" in text
    assert "| 편의점 | 담배소매인 이력 |" in text and "| 1.40× | 통과 |" in text


def test_심사_대상이_없으면_심사_절이_없다():
    assert "## 재포함 심사" not in render_markdown(_report("korean_food", "한식", "permit"), date(2026, 9, 29))


def test_집계_기반_업종은_업종표에_칼표를_단다():
    text = render_markdown(_report("real_estate", "부동산중개업", "aggregate"), date(2026, 9, 29))
    assert "| 부동산중개업 † |" in text


def test_카탈로그에_없는_업종_id는_누락으로_보고한다():
    gate = BacktestGateDto("convenience_store", "편의점", "proxy", True, 1.4, 400, 200, 100, 80, "통과")
    report = _report("convenience_store", "편의점", "proxy", (gate,))
    assert _missing_industry_ids(["convenience_store", "typo_industry"], report) == ["typo_industry"]


def test_요청한_id가_전부_카탈로그에_있으면_누락이_없다():
    gate = BacktestGateDto("convenience_store", "편의점", "proxy", True, 1.4, 400, 200, 100, 80, "통과")
    report = _report("convenience_store", "편의점", "proxy", (gate,))
    assert _missing_industry_ids(["convenience_store"], report) == []
