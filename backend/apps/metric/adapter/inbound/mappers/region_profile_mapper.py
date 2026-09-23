"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.metric.adapter.inbound.api.schemas.region_profile_schema import (
    ProfileMetricValueResponse,
    ProfileTypeResponse,
    RegionProfileResponse,
)
from apps.metric.app.dtos.region_profile_dto import (
    ProfileMetricValueDto,
    ProfileTypeDto,
    RegionProfileDto,
)


_BLOCKS = ("morning", "day", "evening", "night")


def to_response(dto: RegionProfileDto) -> RegionProfileResponse:
    fields = asdict(dto)
    blocks = {block: fields.pop(f"block_{block}") for block in _BLOCKS}
    # 넷이 다 있어야 막대 4개가 선다 — 하나라도 없으면 통째로 null (부분 막대는 오독을 낳는다)
    complete = all(value is not None for value in blocks.values())
    return RegionProfileResponse(**fields, block_intensities=blocks if complete else None)


def to_metric_value_response(dto: ProfileMetricValueDto) -> ProfileMetricValueResponse:
    return ProfileMetricValueResponse(**asdict(dto))


def to_type_response(dto: ProfileTypeDto) -> ProfileTypeResponse:
    return ProfileTypeResponse(**asdict(dto))
