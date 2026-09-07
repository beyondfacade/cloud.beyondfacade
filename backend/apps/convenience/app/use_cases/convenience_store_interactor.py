"""편의점 스냅샷 수집 인터랙터 — 행정동 단위 전량 멱등 업서트.

broker 전례와 달리 폐점 추정(mark_closed)을 하지 않는다: 원천(소진공 상가정보)은
개폐업 분석에 못 쓴다(api.md §2-3). 소실은 last_seen_on이 멈추는 것으로만 기록하고
"사라짐=폐점 추정" 판정은 후속 분석의 몫으로 남긴다 — 관측과 해석의 분리.
"""

from datetime import date
from itertools import batched

from apps.convenience.app.ports.input.convenience_store_use_case import (
    ConvenienceSnapshotUseCase,
)
from apps.convenience.app.ports.output.convenience_store_port import (
    ConvenienceGatewayPort,
    ConvenienceSnapshotRepositoryPort,
)

_CHUNK_SIZE = 500


class ConvenienceSnapshotInteractor(ConvenienceSnapshotUseCase):
    def __init__(
        self,
        repository: ConvenienceSnapshotRepositoryPort,
        gateway: ConvenienceGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(self, region_code: str, observed_on: date) -> int:
        processed = 0
        for chunk in batched(self._gateway.iter_stores(region_code), _CHUNK_SIZE):
            processed += self._repository.upsert(list(chunk), observed_on)
        return processed
