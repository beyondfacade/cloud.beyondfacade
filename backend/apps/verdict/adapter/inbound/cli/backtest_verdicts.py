"""백테스트 한 장 — T 시점 데이터만으로 판정을 다시 내고, T 직후 1년 진입 코호트의 3년 내 폐업률을 판정별로 대조한다 (설계서 §13).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.backtest_verdicts --as-of 2022-06-30 [--out ../docs/verdict-backtest.md]
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

from apps.verdict.app.dtos.region_industry_verdict_dto import BacktestBucketDto, BacktestReportDto, BacktestSignalBucketDto
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.entities.region_industry_verdict_entity import SIGNAL_KEYS
from apps.verdict.domain.services.backtest import VERDICT_ORDER

_LABEL = {"red": "🔴 비추천", "orange": "🟠 조건부", "clear": "⚪ 경고 없음", "insufficient": "판정 보류"}
_SIGNAL_LABEL = {"net_outflow": "순유출", "survival_cliff": "생존 절벽", "early_closure": "조기 폐업", "saturation": "포화", "shrinking": "상권 축소"}


def _pct(rate: float | None) -> str:
    return "—" if rate is None else f"{rate * 100:.1f}%"


def _lift(buckets: list[BacktestBucketDto]) -> str:
    rates = {b.verdict_code: b.rate for b in buckets}
    red, clear = rates.get("red"), rates.get("clear")
    return "—" if not red or not clear else f"{red / clear:.2f}×"


def _rows(buckets: list[BacktestBucketDto]) -> list[str]:
    return [
        f"| {_LABEL[b.verdict_code]} | {b.pairs:,} | {b.opened:,} | {b.closed:,} | {_pct(b.rate)} |"
        for b in sorted(buckets, key=lambda b: VERDICT_ORDER.index(b.verdict_code))
    ]


def _signal_cell(buckets: tuple[BacktestSignalBucketDto, ...], industry: str | None, key: str) -> str:
    side = {b.fired: b for b in buckets if b.industry_id == industry and b.signal_key == key}
    on, off = side.get(True), side.get(False)
    if on is None or off is None or not on.rate or not off.rate:
        return "—"
    return f"{on.rate / off.rate:.2f}× ({on.opened:,})"


def render_markdown(report: BacktestReportDto, today: date) -> str:
    overall = [b for b in report.buckets if b.industry_id is None]
    industries = sorted({b.industry_id for b in report.buckets if b.industry_id is not None})
    lines = [
        f"# 판정 백테스트 — {report.as_of.isoformat()} 시점",
        "",
        f"> 산출 {today.isoformat()}. T = {report.as_of.isoformat()} 시점의 데이터만으로 판정(직전 분기 {report.quarter_max}, 점포수 {report.year_max}년 말)을 다시 내고,",
        f"> T 이후 {report.entry_days}일 안에 개업한 점포가 개업 후 {report.horizon_days}일 안에 폐업했는지 대조했다. 설계서 §13.",
        "",
        "## 전체 (판정 대상 업종 합산)",
        "",
        "| 판정 | 동×업종 | 개업 | 3년 내 폐업 | 폐업률 |",
        "|---|---:|---:|---:|---:|",
        *_rows(overall),
        "",
        f"**lift (🔴 폐업률 ÷ ⚪ 폐업률) = {_lift(overall)}**",
        "",
        "## 업종별",
        "",
        "| 업종 | 🔴 폐업률 (개업) | 🟠 폐업률 (개업) | ⚪ 폐업률 (개업) | 보류 (개업) | lift 🔴/⚪ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for industry in industries:
        cells = {b.verdict_code: b for b in report.buckets if b.industry_id == industry}
        name = next(b.industry_name for b in cells.values()) or industry
        cell = lambda code: f"{_pct(cells[code].rate)} ({cells[code].opened:,})" if code in cells else "—"  # noqa: E731
        lines.append(f"| {name} | {cell('red')} | {cell('orange')} | {cell('clear')} | {cell('insufficient')} | {_lift(list(cells.values()))} |")
    lines += ["", "## 신호별 lift (켜진 동×업종 폐업률 ÷ 꺼진 동×업종 폐업률, 괄호는 켜진 쪽 개업 수)", ""]
    lines += ["| 업종 | " + " | ".join(_SIGNAL_LABEL[k] for k in SIGNAL_KEYS) + " |", "|---|" + "---:|" * len(SIGNAL_KEYS)]
    for industry in [None, *industries]:
        cells = [_signal_cell(report.signal_buckets, industry, key) for key in SIGNAL_KEYS]
        name = "전체" if industry is None else next(b.industry_name for b in report.buckets if b.industry_id == industry) or industry
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## 읽는 법",
        "",
        "- **업종별 표가 정본이다.** 전체 lift에는 업종 구성 효과가 섞인다 — 🔴가 몰린 업종의 기저 폐업률이 높으면 신호와 무관하게 전체 lift가 오른다.",
        "- 판정 보류는 표본 가드(10곳 미만)에 걸린 조합이라 폐업률 비교 대상이 아니다.",
        "- 부동산은 원천(부동산중개업 인허가)에 폐업일이 사실상 없어 폐업률 0%가 나온다 — 해석에서 뺀다. 헬스장도 같은 의심(설계서 §13).",
        "- 개업 수가 두 자리인 칸(당구장·노래방·PC방 등)은 lift가 우연에 흔들린다.",
        "- 신호별 lift는 신호 하나만 떼어 본 것이다(다른 신호 통제 없음). 1.0× 근처면 그 신호는 그 업종에서 동 간 폐업 차이를 못 가른다.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="판정 백테스트 (설계서 §13)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date(2022, 6, 30))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    today = date.today()
    horizon_end = args.as_of + timedelta(days=365 + 1095)
    if horizon_end > today:
        parser.error(f"관측이 안 끝났다: {args.as_of} + 365 + 1095일 = {horizon_end} > 오늘 {today}")
    report = get_region_industry_verdict_use_case().backtest(args.as_of)
    text = render_markdown(report, today)
    if args.out:
        args.out.write_text(text)
        print(f"저장: {args.out}")
    print(text)


if __name__ == "__main__":
    main()
