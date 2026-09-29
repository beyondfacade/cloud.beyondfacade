"""백테스트 한 장 — T 시점 데이터만으로 판정을 다시 내고, T 직후 1년 진입 코호트의 3년 내 폐업률을 판정별로 대조한다 (설계서 §13).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.backtest_verdicts --as-of 2022-06-30 [--out ../docs/verdict-backtest.md]
    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.backtest_verdicts --as-of 2022-06-30 --candidates convenience_store,real_estate
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from apps.verdict.app.dtos.region_industry_verdict_dto import BacktestBucketDto, BacktestReportDto, BacktestSignalBucketDto
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.entities.region_industry_verdict_entity import ALL_SIGNAL_KEYS
from apps.verdict.domain.services.backtest import VERDICT_ORDER

_LABEL = {"red": "🔴 비추천", "orange": "🟠 조건부", "clear": "⚪ 경고 없음", "insufficient": "판정 보류"}
_SIGNAL_LABEL = {
    "net_outflow": "순유출", "survival_cliff": "생존 절벽", "early_closure": "조기 폐업", "saturation": "포화",
    "shrinking": "상권 축소", "closure_rate": "폐업률", "tobacco_gap": "담배권 빈자리",
    "trade_per_office": "사무소당 거래",
}
_BASIS_LABEL = {"permit": "인허가", "proxy": "담배소매인 이력", "aggregate": "상권분석 집계 †"}
_NAME_SUFFIX = {"aggregate": " †"}  # 집계 기반 — 개업 대신 점포수, 3년 폐업 대신 이후 12분기 폐업 (설계서 §7-3)
_VERDICT_CODES: tuple[str, ...] = ("red", "orange", "clear", "insufficient")


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


def _cell_map(buckets: tuple[BacktestBucketDto, ...], industry: str | None) -> dict[str, BacktestBucketDto]:
    return {b.verdict_code: b for b in buckets if b.industry_id == industry}


def _rate_cells(cells: dict[str, BacktestBucketDto]) -> list[str]:
    """판정 코드별 폐업률 (개업) 칸 — 🔴·🟠·⚪·보류 순. 업종별 표·심사 절이 공유하는 서식 (P12)."""
    return [f"{_pct(cells[code].rate)} ({cells[code].opened:,})" if code in cells else "—" for code in _VERDICT_CODES]


def _industry_name(report: BacktestReportDto, industry: str) -> str:
    basis = dict(report.industry_basis).get(industry, "permit")
    name = next((b.industry_name for b in report.buckets if b.industry_id == industry and b.industry_name), industry)
    return name + _NAME_SUFFIX.get(basis, "")


def _signal_lines(report: BacktestReportDto, industries: list[str | None]) -> list[str]:
    lines = [
        "| 업종 | " + " | ".join(_SIGNAL_LABEL[k] for k in ALL_SIGNAL_KEYS) + " |",
        "|---|" + "---:|" * len(ALL_SIGNAL_KEYS),
    ]
    for industry in industries:
        cells = [_signal_cell(report.signal_buckets, industry, key) for key in ALL_SIGNAL_KEYS]
        name = "전체" if industry is None else _industry_name(report, industry)
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines


def _candidate_lines(report: BacktestReportDto) -> list[str]:
    lines = [
        "", "## 재포함 심사 — 업종 특화 원천 (업종 특화 신호 설계서 §8)", "",
        "> 게이트: 경고(🔴+🟠) 폐업률 ÷ ⚪ 폐업률 ≥ 1.10×. 표본 — 담배소매인 이력은 경고·⚪ 개업 각 50곳 이상, "
        "상권분석 집계는 경고·⚪ 동 각 30곳 이상. 판정 대상 여부와 무관하게 이 업종들만 다시 판정했다.",
        "> † 집계 기반: 괄호 안은 개업 수가 아니라 T 분기 점포수, 폐업은 이후 12분기 폐업 수.",
        "",
        "| 업종 | 원천 | 🔴 폐업률 (개업) | 🟠 폐업률 (개업) | ⚪ 폐업률 (개업) | 보류 (개업) | 경고 lift | 게이트 |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for gate in report.gates:
        cells = _cell_map(report.buckets, gate.industry_id)
        lift = "—" if gate.warn_lift is None else f"{gate.warn_lift:.2f}×"
        lines.append(
            f"| {gate.industry_name or gate.industry_id} | {_BASIS_LABEL[gate.basis]} | " + " | ".join(_rate_cells(cells))
            + f" | {lift} | {gate.reason} |"
        )
    lines += ["", "### 심사 업종 신호별 lift", "", *_signal_lines(report, [g.industry_id for g in report.gates])]
    return lines


def _missing_industry_ids(requested: list[str], report: BacktestReportDto) -> list[str]:
    """--candidates로 준 업종 id 중 카탈로그에 없는 것 — named_industries가 모르는 id를 조용히 버리므로
    CLI가 대신 알려야 한다 (업종 특화 신호 설계서 §8, Task 6 리뷰)."""
    known = dict(report.industry_basis)
    return [industry_id for industry_id in requested if industry_id not in known]


def render_markdown(report: BacktestReportDto, today: date, candidates: BacktestReportDto | None = None) -> str:
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
        cells = _cell_map(report.buckets, industry)
        name = _industry_name(report, industry)
        lines.append(f"| {name} | " + " | ".join(_rate_cells(cells)) + f" | {_lift(list(cells.values()))} |")
    lines += ["", "## 신호별 lift (켜진 동×업종 폐업률 ÷ 꺼진 동×업종 폐업률, 괄호는 켜진 쪽 개업 수)", ""]
    lines += _signal_lines(report, [None, *industries])
    lines += [
        "",
        "## 읽는 법",
        "",
        "- **업종별 표가 정본이다.** 전체 lift에는 업종 구성 효과가 섞인다 — 🔴가 몰린 업종의 기저 폐업률이 높으면 신호와 무관하게 전체 lift가 오른다.",
        "- 판정 보류는 표본 가드(10곳 미만)에 걸린 조합이라 폐업률 비교 대상이 아니다.",
        "- 편의점·부동산은 업종 특화 원천(담배소매인 이력·상권분석 집계)으로 재포함 심사를 받았으나 9/29 게이트(경고 lift ≥ 1.10×)에 "
        "둘 다 미달해 판정 대상에서 계속 뺀다 — 아래 재포함 심사 절. "
        "† 표시 업종은 집계 기반이라 개업 대신 T 분기 점포수, 3년 내 폐업 대신 이후 12분기 폐업 수를 세며 전체 합산에 넣지 않는다. "
        "헬스장은 원천 확인 결과 정상(연 3% 폐업이 실제)이라 그대로 둔다.",
        "- 편의점 승계 접기는 폐업 ±90일 안 같은 지번 새 지정을 한 영업으로 잇는다 — T 직전 폐업이 T 뒤 90일 안 새 지정으로 접히면 "
        "T 이후 최대 90일을 내다본 셈이라 작은 미래 참조 편향이 있다(고치지 않고 기록만 한다).",
        "- 개업 수가 두 자리인 칸(당구장·노래방·PC방 등)은 lift가 우연에 흔들린다.",
        "- 신호별 lift는 신호 하나만 떼어 본 것이다(다른 신호 통제 없음). 1.0× 근처면 그 신호는 그 업종에서 동 간 폐업 차이를 못 가른다.",
    ]
    lines += _candidate_lines(candidates) if candidates is not None else []
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="판정 백테스트 (설계서 §13)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date(2022, 6, 30))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--candidates", type=lambda s: [x for x in s.split(",") if x], default=None,
        help="판정 제외 업종을 따로 심사 (예: convenience_store,real_estate) — 업종 특화 신호 설계서 §8",
    )
    args = parser.parse_args()
    today = date.today()
    horizon_end = args.as_of + timedelta(days=365 + 1095)
    if horizon_end > today:
        parser.error(f"관측이 안 끝났다: {args.as_of} + 365 + 1095일 = {horizon_end} > 오늘 {today}")
    use_case = get_region_industry_verdict_use_case()
    report = use_case.backtest(args.as_of)
    candidates = use_case.backtest(args.as_of, industry_ids=args.candidates) if args.candidates else None
    if candidates is not None:
        missing = _missing_industry_ids(args.candidates, candidates)
        if missing:
            print(f"경고: 카탈로그에 없는 업종 id: {', '.join(missing)}", file=sys.stderr)
    text = render_markdown(report, today, candidates)
    if args.out:
        args.out.write_text(text)
        print(f"저장: {args.out}")
    print(text)


if __name__ == "__main__":
    main()
