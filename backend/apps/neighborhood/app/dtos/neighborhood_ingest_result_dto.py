"""적재 결과 DTO — 7종이 형태가 같아 단일 원천으로 둔다 (commerce의 sales/breakdown DTO 전례)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NeighborhoodIngestResultDto:
    processed: int  # 업서트한 행 수
    region_resolved: int  # region_code를 채운 행 수
    region_unresolved: int  # 원천에만 있는 옛 행정동 — 버리지 않고 NULL로 남긴 행 수
