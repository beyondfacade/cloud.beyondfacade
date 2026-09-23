"""서울 평균 적재 인터랙터 — 유일하게 region 해석이 없다 (키가 분기뿐이라 행정동이 없다).

`region_commerce_change`가 `year_quarter`를 FK로 참조하므로 **이쪽이 먼저 적재돼야 한다**
(설계서 §3-5). 중복 제거는 게이트웨이가 한다 — 9,350행 원천에서 분기 22개만 나온다.
"""

from pathlib import Path

from apps.neighborhood.app.dtos.seoul_commerce_change_baseline_dto import (
    NeighborhoodIngestResultDto,
)
from apps.neighborhood.app.ports.input.seoul_commerce_change_baseline_use_case import (
    SeoulCommerceChangeBaselineIngestUseCase,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_port import (
    SeoulCommerceChangeBaselineGatewayPort,
    SeoulCommerceChangeBaselineRepositoryPort,
)


class SeoulCommerceChangeBaselineIngestInteractor(SeoulCommerceChangeBaselineIngestUseCase):
    def __init__(
        self,
        repository: SeoulCommerceChangeBaselineRepositoryPort,
        gateway: SeoulCommerceChangeBaselineGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(self, paths: list[Path]) -> NeighborhoodIngestResultDto:
        processed = 0
        for path in paths:
            processed += self._repository.upsert(list(self._gateway.fetch_baselines(path)))
        return NeighborhoodIngestResultDto(
            processed=processed, region_resolved=0, region_unresolved=0
        )
