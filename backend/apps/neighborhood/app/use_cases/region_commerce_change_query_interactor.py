from collections.abc import Callable

from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    ChangeMetricValueDto,
    RegionCommerceChangeDto,
    SeoulBaselineDto,
)
from apps.neighborhood.app.ports.input.region_commerce_change_query_use_case import (
    RegionCommerceChangeQueryUseCase,
)
from apps.neighborhood.app.ports.output.region_commerce_change_query_port import (
    RegionCommerceChangeQueryPort,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_query_port import (
    SeoulCommerceChangeBaselineQueryPort,
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
    def __init__(
        self,
        query: RegionCommerceChangeQueryPort,
        baseline: SeoulCommerceChangeBaselineQueryPort,
    ) -> None:
        self._query = query
        self._baseline = baseline

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

    def find_with_baseline(
        self, region_code: str, year_quarter: str | None
    ) -> RegionCommerceChangeDto | None:
        row = (
            self._query.find(region_code, year_quarter)
            if year_quarter
            else self._query.find_latest(region_code)
        )
        if row is None or row.region_code is None:
            return None
        baseline = self._baseline.find(row.year_quarter)
        return RegionCommerceChangeDto(
            region_code=row.region_code,
            year_quarter=row.year_quarter,
            change_code=row.change_code,
            change_name=row.change_name,
            operating_months=row.operating_months,
            closed_months=row.closed_months,
            seoul=None
            if baseline is None
            else SeoulBaselineDto(
                operating_months=baseline.seoul_operating_months,
                closed_months=baseline.seoul_closed_months,
            ),
        )
