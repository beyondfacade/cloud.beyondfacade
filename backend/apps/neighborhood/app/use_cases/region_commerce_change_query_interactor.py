from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
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


class RegionCommerceChangeQueryInteractor(RegionCommerceChangeQueryUseCase):
    def __init__(
        self,
        query: RegionCommerceChangeQueryPort,
        baseline: SeoulCommerceChangeBaselineQueryPort,
    ) -> None:
        self._query = query
        self._baseline = baseline

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
