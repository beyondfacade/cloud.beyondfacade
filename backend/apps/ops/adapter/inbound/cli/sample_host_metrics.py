"""설비 지표 1분 표본 적재 — 매분 크론(scripts/host-metrics-sampler.sh)이 부른다.

    python -m apps.ops.adapter.inbound.cli.sample_host_metrics
"""

from apps.ops.dependencies.ops_dependencies import get_host_history_use_case


def main() -> None:
    point, pruned = get_host_history_use_case().sample()
    print(f"표본 {point.t:%H:%M} · CPU {point.cpu_percent}% · 메모리 {point.memory_percent}% · 지운 표본 {pruned}건")


if __name__ == "__main__":
    main()
