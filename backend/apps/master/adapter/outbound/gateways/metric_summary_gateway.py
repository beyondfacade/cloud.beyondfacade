"""Driven Adapter — metric BC UseCase 호출로 지표 스냅샷 취득 (cross-BC는 어댑터 레이어에서만)."""

from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.app.ports.output.region_port import RegionMetricSummaryPort
from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)

_LATEST_YEAR = 2026  # 사이드패널 카드 기준 연도 (build_metrics 적재 범위의 최신)


class MetricSummaryGateway(RegionMetricSummaryPort):
    def fetch(self, region_code: str, industry_id: str) -> RegionMetricSnapshot | None:
        dto = get_region_industry_metric_use_case().find(
            region_code, industry_id, _LATEST_YEAR
        )
        if dto is None:
            return None
        return RegionMetricSnapshot(
            store_count=dto.store_count,
            closure_rate=dto.closure_rate,
            growth_rate=dto.growth_rate,
        )
