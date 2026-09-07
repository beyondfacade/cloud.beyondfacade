"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.metric.adapter.inbound.api.schemas.region_industry_metric_schema import (
    MetricValueResponse,
    RegionIndustryMetricResponse,
)
from apps.metric.app.dtos.region_industry_metric_dto import (
    MetricValueDto,
    RegionIndustryMetricDto,
)


def to_response(dto: RegionIndustryMetricDto) -> RegionIndustryMetricResponse:
    return RegionIndustryMetricResponse(**asdict(dto))


def to_metric_value_response(dto: MetricValueDto) -> MetricValueResponse:
    return MetricValueResponse(**asdict(dto))
