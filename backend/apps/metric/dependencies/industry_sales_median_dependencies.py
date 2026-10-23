"""Composition Root (DIP) — Port에 Adapter를 주입한다."""

from apps.metric.adapter.outbound.repositories.industry_sales_median_repository import (
    SqlAlchemyIndustrySalesMedianRepository,
)
from apps.metric.app.ports.input.industry_sales_median_use_case import IndustrySalesMedianUseCase
from apps.metric.app.use_cases.industry_sales_median_interactor import IndustrySalesMedianInteractor


def get_industry_sales_median_use_case() -> IndustrySalesMedianUseCase:
    return IndustrySalesMedianInteractor(repository=SqlAlchemyIndustrySalesMedianRepository())
