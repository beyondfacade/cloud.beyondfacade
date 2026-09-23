"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.neighborhood.adapter.outbound.repositories.region_commerce_change_query_repository import (
    SqlAlchemyRegionCommerceChangeQueryRepository,
)
from apps.neighborhood.adapter.outbound.repositories.seoul_commerce_change_baseline_query_repository import (
    SqlAlchemySeoulCommerceChangeBaselineQueryRepository,
)
from apps.neighborhood.app.ports.input.region_commerce_change_query_use_case import (
    RegionCommerceChangeQueryUseCase,
)
from apps.neighborhood.app.use_cases.region_commerce_change_query_interactor import (
    RegionCommerceChangeQueryInteractor,
)


def get_region_commerce_change_query_use_case() -> RegionCommerceChangeQueryUseCase:
    return RegionCommerceChangeQueryInteractor(
        query=SqlAlchemyRegionCommerceChangeQueryRepository(),
        baseline=SqlAlchemySeoulCommerceChangeBaselineQueryRepository(),
    )
