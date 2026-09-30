from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.dependencies.admin_guard import require_admin, require_operator
from apps.ops.adapter.inbound.api.query_params import USAGE_SERIES_HOURS, one_of
from apps.ops.adapter.inbound.api.schemas.healthcare_schema import (
    HealthcareSnapshotResponse,
    LlmRouteResponse,
    ProbeRequest,
    ProbeResultResponse,
)
from apps.ops.adapter.inbound.api.schemas.ops_history_schema import UsageSeriesResponse
from apps.ops.adapter.inbound.mappers.healthcare_mapper import (
    to_probe_response,
    to_route_response,
    to_snapshot_response,
)
from apps.ops.adapter.inbound.mappers.ops_history_mapper import to_actor, to_usage_series_response
from apps.ops.app.ports.input.healthcare_use_case import HealthcareUseCase
from apps.ops.dependencies.ops_dependencies import get_healthcare_use_case

router = APIRouter(prefix="/admin/healthcare", tags=["admin"])


@router.get("/myself", response_model=LlmRouteResponse)
def myself(use_case: HealthcareUseCase = Depends(get_healthcare_use_case)) -> LlmRouteResponse:
    return to_route_response(use_case.myself())


@router.get("/snapshot", response_model=HealthcareSnapshotResponse, dependencies=[Depends(require_admin)])
def snapshot(use_case: HealthcareUseCase = Depends(get_healthcare_use_case)) -> HealthcareSnapshotResponse:
    return to_snapshot_response(use_case.snapshot())


@router.get("/usage-series", response_model=UsageSeriesResponse, dependencies=[Depends(require_admin)])
def usage_series(
    hours: Annotated[int, Query(), one_of(USAGE_SERIES_HOURS)] = 24,
    use_case: HealthcareUseCase = Depends(get_healthcare_use_case),
) -> UsageSeriesResponse:
    return to_usage_series_response(use_case.usage_series(hours))


# 프로브는 실제 LLM 호출(토큰 비용)이 나가므로 운영 관리자만
@router.post("/probe", response_model=ProbeResultResponse)
def probe(
    body: ProbeRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: HealthcareUseCase = Depends(get_healthcare_use_case),
) -> ProbeResultResponse:
    actor = to_actor(principal, client_ip_from_scope(request.scope))
    return to_probe_response(use_case.probe(body.kind, body.message, actor))
