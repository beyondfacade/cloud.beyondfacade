"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.ops.adapter.inbound.api.schemas.ops_history_schema import (
    CollectorLogResponse,
    CollectorRunResponse,
    HostHistoryResponse,
    UsageSeriesResponse,
)
from apps.ops.app.dtos.ops_history_dto import (
    CollectorLogDto,
    CollectorRunDto,
    HostHistoryDto,
    OpsActorDto,
    UsageSeriesDto,
)


def to_actor(principal: AdminPrincipalDto, ip: str | None) -> OpsActorDto:
    return OpsActorDto(id=principal.id, username=principal.username, ip=ip)


def to_history_response(dto: HostHistoryDto) -> HostHistoryResponse:
    return HostHistoryResponse.model_validate(asdict(dto))


def to_usage_series_response(dto: UsageSeriesDto) -> UsageSeriesResponse:
    return UsageSeriesResponse.model_validate(asdict(dto))


def to_log_response(dto: CollectorLogDto) -> CollectorLogResponse:
    return CollectorLogResponse.model_validate(asdict(dto))


def to_run_response(dto: CollectorRunDto) -> CollectorRunResponse:
    return CollectorRunResponse.model_validate(asdict(dto))
