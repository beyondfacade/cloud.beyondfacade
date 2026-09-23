"""7개 인터랙터가 공유하는 적재 절차 — Template Method (CLAUDE.md §5).

절차는 하나다: 원천 스트림을 청크로 끊어 받아 → region을 해석해 채우고 → 멱등 업서트한다.
테이블마다 다른 것은 엔티티 타입과 게이트웨이 메서드 이름뿐이라, 같은 루프를 7번 베껴 쓰는 대신
여기 한 벌만 둔다. 각 인터랙터는 자기 포트를 구현하는 얇은 껍데기로 남는다.

`dataclasses.replace`로 region_code만 갈아끼우는 근거: 엔티티가 frozen이라 제자리 수정이 없고,
어떤 엔티티든 `adstrd_code`·`region_code` 두 필드만 있으면 동작한다.
"""

from collections.abc import Callable, Iterator
from dataclasses import replace
from itertools import islice
from pathlib import Path
from typing import Protocol, TypeVar

from apps.neighborhood.app.dtos.neighborhood_ingest_result_dto import NeighborhoodIngestResultDto
from apps.neighborhood.app.ports.output.region_catalog_port import RegionCatalogPort

CHUNK_SIZE = 40_000  # 커밋 1회당 행 수 — 상주 메모리와 트랜잭션 크기를 동시에 묶는 값

T = TypeVar("T")


class _Repository(Protocol[T]):
    def upsert(self, rows: list[T]) -> int: ...


def chunks(rows: Iterator[T], size: int) -> Iterator[list[T]]:
    while chunk := list(islice(rows, size)):
        yield chunk


def ingest_with_region(
    paths: list[Path],
    stream: Callable[[Path], Iterator[T]],
    repository: _Repository[T],
    region_catalog: RegionCatalogPort,
) -> NeighborhoodIngestResultDto:
    """원천 → region 해석 → 청크 업서트. 미매칭 행은 버리지 않고 region_code NULL로 남긴다."""
    region_by_adstrd = region_catalog.region_code_by_adstrd()
    processed = resolved = 0
    for path in paths:
        for chunk in chunks(iter(stream(path)), CHUNK_SIZE):
            rows = [
                replace(row, region_code=region_by_adstrd.get(row.adstrd_code)) for row in chunk
            ]
            processed += repository.upsert(rows)
            resolved += sum(1 for row in rows if row.region_code is not None)
    return NeighborhoodIngestResultDto(
        processed=processed,
        region_resolved=resolved,
        region_unresolved=processed - resolved,
    )
