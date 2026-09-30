"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.ops.adapter.inbound.api.schemas.facility_schema import FacilitySnapshotResponse, ServiceCheckResponse
from apps.ops.app.dtos.facility_dto import FacilitySnapshotDto, ServiceCheckDto


def to_service_response(dto: ServiceCheckDto) -> ServiceCheckResponse:
    return ServiceCheckResponse(**asdict(dto))


def to_snapshot_response(dto: FacilitySnapshotDto) -> FacilitySnapshotResponse:
    return FacilitySnapshotResponse.model_validate(asdict(dto))
