"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.neighborhood.adapter.inbound.api.schemas.region_commerce_change_schema import (
    ChangeMetricValueResponse,
    RegionCommerceChangeResponse,
)
from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    ChangeMetricValueDto,
    RegionCommerceChangeDto,
)


def to_response(dto: RegionCommerceChangeDto) -> RegionCommerceChangeResponse:
    return RegionCommerceChangeResponse(**asdict(dto))


def to_metric_value_response(dto: ChangeMetricValueDto) -> ChangeMetricValueResponse:
    return ChangeMetricValueResponse(**asdict(dto))
