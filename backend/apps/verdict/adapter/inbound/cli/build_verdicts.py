"""판정 배치 — 매일 04:20 store-collector.sh에서 build_metrics 바로 뒤에 실행 (설계서 §4-4).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts
"""

from datetime import date

from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case


def main() -> None:
    processed = get_region_industry_verdict_use_case().build(date.today())
    print(f"판정 업서트: {processed}건 (판정 대상 13업종 × 행정동)")


if __name__ == "__main__":
    main()
