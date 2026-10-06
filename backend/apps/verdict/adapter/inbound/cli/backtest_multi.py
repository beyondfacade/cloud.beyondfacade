"""여러 시점 백테스트 — T마다 운영 판정·운영 신호(use_case.backtest 그대로)와 백테스트 전용 후보 신호를 같은 셈법으로 대조하고,
T 간 안정성을 한 표로 낸다. 운영 판정 배치·API와 무관(읽기만). 후보 신호 재료 읽기는 게이트웨이에서만 (real_estate_survivor_backcast 전례).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.backtest_multi [--out ../docs/verdict-backtest-multi.md]
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from pathlib import Path

from apps.verdict.adapter.inbound.cli.backtest_verdicts import _cell_map, _lift, _rate_cells, _rows
from apps.verdict.adapter.outbound.gateways.candidate_signal_gateway import CandidateSignalGateway
from apps.verdict.adapter.outbound.gateways.entrant_outcome_gateway import EntrantOutcomeGateway
from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.entities.region_industry_verdict_entity import SIGNAL_KEYS
from apps.verdict.domain.services.backtest import quarter_before, shift_quarter
from apps.verdict.domain.services.candidate_signals import (
    Key,
    fired_flags,
    opening_rush,
    sales_trend,
    saturation_demand,
    stable_hits,
    summarize_candidate,
)
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS

# (T, 추적 일수) — 2023은 3년 추적이 아직 안 끝나 2년
PERIODS: tuple[tuple[date, int], ...] = (
    (date(2019, 6, 30), 1095), (date(2021, 6, 30), 1095), (date(2022, 6, 30), 1095), (date(2023, 6, 30), 730),
)
ENTRY_DAYS = 365
DATA_LAG_DAYS = 90  # 추적 끝 ≤ 오늘 − 90일 (폐업 신고가 늦게 들어오는 여유)
MIN_LIFT, MIN_OPENED = 1.10, 50  # 재포함 게이트와 같은 기준 (backtest.GATE_POLICIES permit)

_LABELS = {
    "net_outflow": "순유출", "survival_cliff": "생존 절벽", "early_closure": "조기 폐업", "saturation": "포화",
    "shrinking": "상권 축소",
    "saturation_demand": "포화(상주+직장)", "saturation_footfall": "포화(+유동)", "opening_rush": "개업 러시",
    "sales_trend": "매출 추세",
}
_WORSE: dict[str, Callable[[float], float]] = {
    "saturation_demand": lambda v: v, "saturation_footfall": lambda v: v, "opening_rush": lambda v: v,
    "sales_trend": lambda v: -v,  # 하락이 나쁨
}
CANDIDATE_KEYS: tuple[str, ...] = tuple(_WORSE)
KEYS: tuple[str, ...] = SIGNAL_KEYS + CANDIDATE_KEYS


def candidate_values(as_of: date, industry_ids: set[str]) -> dict[str, dict[Key, float | None]]:
    t, quarter = DEFAULT_THRESHOLDS, quarter_before(as_of)
    gateway = CandidateSignalGateway()
    stats = [s for s in StoreSignalStatsGateway().signal_stats(as_of) if s.industry_id in industry_ids]
    counts = [c for c in RegionContextGateway().latest_store_counts(as_of.year - 1) if c.industry_id in industry_ids]
    demand = gateway.demand(quarter)
    resident_worker = {r: n + demand.workers[r] for r, n in demand.residents.items() if r in demand.workers}
    with_footfall = {r: n + demand.footfall_daily[r] for r, n in resident_worker.items() if r in demand.footfall_daily}
    now, prev = gateway.sales(quarter, industry_ids), gateway.sales(shift_quarter(quarter, -4), industry_ids)
    return {
        "saturation_demand": {
            (c.region_code, c.industry_id): saturation_demand(c.store_count, resident_worker.get(c.region_code), t.min_population)
            for c in counts
        },
        "saturation_footfall": {
            (c.region_code, c.industry_id): saturation_demand(c.store_count, with_footfall.get(c.region_code), t.min_population)
            for c in counts
        },
        "opening_rush": {
            (s.region_code, s.industry_id): opening_rush(s.opened_12m, s.start_store_count, t.min_sample) for s in stats
        },
        "sales_trend": {key: sales_trend(*now[key], *prev.get(key, (None, None)), t.min_sample) for key in now},
    }


def lift_cell(buckets: Sequence, industry: str | None, key: str) -> tuple[float, int, int] | None:
    """(켜짐 폐업률 ÷ 꺼짐 폐업률, 켜짐 개업, 꺼짐 개업). 한쪽이 없거나 폐업률 0이면 None."""
    side = {b.fired: b for b in buckets if b.industry_id == industry and b.signal_key == key}
    on, off = side.get(True), side.get(False)
    if on is None or off is None or not on.rate or not off.rate:
        return None
    return on.rate / off.rate, on.opened, off.opened


def _fmt_cell(cell: tuple[float, int, int] | None) -> str:
    if cell is None:
        return "—"
    lift, on, off = cell
    mark = "*" if min(on, off) < MIN_OPENED else ""
    return f"{lift:.2f}×{mark} ({on:,})"


def _evaluated(buckets: Sequence, key: str) -> int:
    return sum(b.pairs for b in buckets if b.industry_id is None and b.signal_key == key)


def run_period(use_case, as_of: date, horizon: int, industries) -> dict:
    ids = {i.industry_id for i in industries}
    report = use_case.backtest(as_of, entry_days=ENTRY_DAYS, horizon_days=horizon)
    outcomes = [o for o in EntrantOutcomeGateway().entrant_outcomes(as_of, ENTRY_DAYS, horizon) if o.industry_id in ids]
    candidate_buckets = [
        bucket
        for key, values in candidate_values(as_of, ids).items()
        for bucket in summarize_candidate(key, fired_flags(values, _WORSE[key], DEFAULT_THRESHOLDS.on_percentile), outcomes)
    ]
    return {"report": report, "signal_buckets": [*report.signal_buckets, *candidate_buckets]}


def _period_lines(period: dict, names: dict[str, str]) -> list[str]:
    report, buckets = period["report"], period["signal_buckets"]
    years = report.horizon_days // 365
    overall = [b for b in report.buckets if b.industry_id is None]
    lines = [
        f"## T = {report.as_of.isoformat()} — 직전 분기 {report.quarter_max} · 점포수 {report.year_max}년 말 · "
        f"진입 {report.entry_days}일 · 추적 {years}년",
        "",
        "평가된 동×업종 수 (가드 통과, 0이면 그 T에 계산 불가): "
        + " · ".join(f"{_LABELS[k]} {_evaluated(buckets, k):,}" for k in KEYS),
        "",
        "### 판정 — 전체",
        "",
        f"| 판정 | 동×업종 | 개업 | {years}년 내 폐업 | 폐업률 |",
        "|---|---:|---:|---:|---:|",
        *_rows(overall),
        "",
        f"**lift (🔴 ÷ ⚪) = {_lift(overall)}**",
        "",
        "### 판정 — 업종별",
        "",
        "| 업종 | 🔴 폐업률 (개업) | 🟠 폐업률 (개업) | ⚪ 폐업률 (개업) | 보류 (개업) | lift 🔴/⚪ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for industry in sorted(names):
        cells = _cell_map(report.buckets, industry)
        lines.append(f"| {names[industry]} | " + " | ".join(_rate_cells(cells)) + f" | {_lift(list(cells.values()))} |")
    lines += [
        "",
        "### 신호 × 업종 lift (켜짐 폐업률 ÷ 꺼짐 폐업률, 괄호는 켜짐 쪽 개업 수, * = 켜짐·꺼짐 중 개업 50곳 미만)",
        "",
        "| 업종 | " + " | ".join(_LABELS[k] for k in KEYS) + " |",
        "|---|" + "---:|" * len(KEYS),
    ]
    for industry in [None, *sorted(names)]:
        name = "전체" if industry is None else names[industry]
        lines.append(f"| {name} | " + " | ".join(_fmt_cell(lift_cell(buckets, industry, k)) for k in KEYS) + " |")
    return [*lines, ""]


def _stability_lines(periods: list[dict], names: dict[str, str]) -> list[str]:
    ts = " · ".join(p["report"].as_of.strftime("%Y") for p in periods)
    lines = [
        "## 안정성 — 신호 × 업종",
        "",
        f"> 칸 = **k/n** 뒤에 T별 lift({ts} 순). n = 켜짐·꺼짐 개업이 각 {MIN_OPENED}곳 이상인 T 수, "
        f"k = 그중 lift ≥ {MIN_LIFT:.2f}×인 T 수. * = 표본 부족(n에서 뺌), – = 그 T에 계산 불가.",
        "",
        "| 업종 | " + " | ".join(_LABELS[k] for k in KEYS) + " |",
        "|---|" + "---|" * len(KEYS),
    ]
    for industry in [None, *sorted(names)]:
        name = "전체" if industry is None else names[industry]
        cells = []
        for key in KEYS:
            per_t = [lift_cell(p["signal_buckets"], industry, key) for p in periods]
            hits, n = stable_hits(per_t, MIN_LIFT, MIN_OPENED)
            trail = "·".join(
                "–" if c is None else f"{c[0]:.2f}" + ("*" if min(c[1], c[2]) < MIN_OPENED else "") for c in per_t
            )
            cells.append(f"**{hits}/{n}** {trail}")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return [*lines, ""]


def render(periods: list[dict], names: dict[str, str], today: date) -> str:
    lines = [
        "# 판정 백테스트 — 여러 시점 · 후보 신호",
        "",
        f"> 산출 {today.isoformat()}. `backtest_multi` CLI. T마다 그 시점 데이터만으로 판정을 다시 내고(운영 규칙·임계값 그대로), "
        f"T 이후 {ENTRY_DAYS}일 안에 개업한 점포가 개업 후 추적 기간 안에 폐업했는지 대조했다. "
        "후보 신호 4개는 백테스트에서만 계산했다 — 운영 판정에는 들어가지 않는다.",
        "",
        "**후보 신호 정의** (켜짐 = 업종 안 백분위 75 이상 — 운영 신호 on 기준과 같다. 가드 미달 동은 분포·집계에서 뺀다)",
        "",
        "- **포화(상주+직장)** = T 직전 연말 점포수(운영 포화와 같은 분자, region_industry_metric) ÷ ((상주인구 + 직장인구) ÷ 1,000). "
        "인구는 직전 분기 region_population_quarter 총계. 가드: 수요 1,000명 이상, 직장인구 없는 동은 뺀다(0으로 채우지 않음). 높을수록 나쁨.",
        "- **포화(+유동)** = 같은 분자 ÷ ((상주 + 직장 + 일평균 유동인구) ÷ 1,000). 유동인구 = 직전 분기 region_footfall_quarter 총계 ÷ 분기 일수. "
        "일평균 유동은 중위 동에서 상주+직장의 약 2.2배(0.1~18배)라 분모의 3분의 2가량이 유동인구다.",
        "- **개업 러시** = T 전 12개월 개업 ÷ 12개월 전 영업 점포 (store, 순유출과 같은 재료·가드 10곳). 높을수록 나쁨.",
        "- **매출 추세** = 점포당 분기 추정매출(직전 분기, region_commerce_sales 합 ÷ region_commerce_store 점포수 합) ÷ 전년 동분기 값 − 1. "
        "가드: 두 분기 점포 각 10곳. 낮을수록 나쁨.",
        "",
        *[line for period in periods for line in _period_lines(period, names)],
        *_stability_lines(periods, names),
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="여러 시점 판정 백테스트 + 후보 신호 (실험)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    today = date.today()
    cutoff = today - timedelta(days=DATA_LAG_DAYS)
    use_case = get_region_industry_verdict_use_case()
    industries = IndustryCatalogGateway().judged_industries()
    names = {i.industry_id: i.name for i in industries}
    periods = []
    for as_of, horizon in PERIODS:
        end = as_of + timedelta(days=ENTRY_DAYS + horizon)
        if end > cutoff:
            print(f"건너뜀: T={as_of} 추적 끝 {end} > 오늘−{DATA_LAG_DAYS}일 {cutoff}", file=sys.stderr)
            continue
        print(f"T={as_of} 추적 {horizon}일 …", file=sys.stderr)
        periods.append(run_period(use_case, as_of, horizon, industries))
    text = render(periods, names, today)
    if args.out:
        args.out.write_text(text)
        print(f"저장: {args.out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
