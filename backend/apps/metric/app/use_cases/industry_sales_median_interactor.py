from apps.metric.app.ports.input.industry_sales_median_use_case import IndustrySalesMedianUseCase
from apps.metric.app.ports.output.industry_sales_median_port import IndustrySalesMedianRepositoryPort


class IndustrySalesMedianInteractor(IndustrySalesMedianUseCase):
    def __init__(self, repository: IndustrySalesMedianRepositoryPort) -> None:
        self._repository = repository

    def build(self) -> int:
        return self._repository.rebuild()
