"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.ops.adapter.inbound.api.schemas.healthcare_schema import (
    HealthcareSnapshotResponse,
    LlmRouteResponse,
    ProbeResultResponse,
)
from apps.ops.app.dtos.healthcare_dto import HealthcareSnapshotDto, LlmRouteDto, ProbeResultDto


def to_route_response(dto: LlmRouteDto) -> LlmRouteResponse:
    return LlmRouteResponse(**asdict(dto))


def to_snapshot_response(dto: HealthcareSnapshotDto) -> HealthcareSnapshotResponse:
    return HealthcareSnapshotResponse.model_validate(asdict(dto))


def to_probe_response(dto: ProbeResultDto) -> ProbeResultResponse:
    return ProbeResultResponse.model_validate(asdict(dto))
