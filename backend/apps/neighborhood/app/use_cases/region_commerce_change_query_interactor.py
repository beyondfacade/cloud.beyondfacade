from collections.abc import Callable

from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    ChangeMetricValueDto,
    RegionCommerceChangeDto,
)
from apps.neighborhood.app.ports.input.region_commerce_change_query_use_case import (
    RegionCommerceChangeQueryUseCase,
)
from apps.neighborhood.app.ports.output.region_commerce_change_query_port import (
    RegionCommerceChangeQueryPort,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import (
    RegionCommerceChange,
)
from apps.neighborhood.domain.errors import MetricNotFoundError

# Strategy (GoF) — metric 이름 → 값 추출. if/elif 분기 대신 테이블 디스패치 (metric BC 전례)
_METRIC_EXTRACTORS: dict[str, Callable[[RegionCommerceChange], float | None]] = {
    "operating_months": lambda row: row.operating_months,
}


class RegionCommerceChangeQueryInteractor(RegionCommerceChangeQueryUseCase):
    def __init__(self, query: RegionCommerceChangeQueryPort) -> None:
        self._query = query

    def myself(self) -> RegionCommerceChangeDto:
        return RegionCommerceChangeDto(
            region_code="myself",
            year_quarter="20262",
            change_code="LL",
            change_name="다이나믹",
            operating_months=1.0,
            closed_months=1.0,
        )

    def list_metric_values(
        self, metric: str, year_quarter: str | None
    ) -> list[ChangeMetricValueDto]:
        extractor = _METRIC_EXTRACTORS.get(metric)
        if extractor is None:
            raise MetricNotFoundError(metric)
        quarter = year_quarter or self._query.latest_quarter()
        if quarter is None:
            return []  # 적재 전
        return [
            ChangeMetricValueDto(region_code=row.region_code, value=float(value))
            # 원천 공란을 0으로 내보내면 "가장 빨리 닫는 동네"로 색칠된다
            for row in self._query.list_by_quarter(quarter)
            if row.region_code is not None and (value := extractor(row)) is not None
        ]
