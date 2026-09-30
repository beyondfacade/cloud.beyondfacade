from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.dependencies.admin_guard import require_admin, require_operator
from apps.ops.adapter.inbound.api.query_params import HOST_HISTORY_HOURS, one_of
from apps.ops.adapter.inbound.api.schemas.facility_schema import FacilitySnapshotResponse, ServiceCheckResponse
from apps.ops.adapter.inbound.api.schemas.ops_history_schema import (
    CollectorLogResponse,
    CollectorRunResponse,
    HostHistoryResponse,
)
from apps.ops.adapter.inbound.mappers.facility_mapper import to_service_response, to_snapshot_response
from apps.ops.adapter.inbound.mappers.ops_history_mapper import (
    to_actor,
    to_history_response,
    to_log_response,
    to_run_response,
)
from apps.ops.app.ports.input.collector_tools_use_case import CollectorToolsUseCase
from apps.ops.app.ports.input.facility_use_case import FacilityUseCase
from apps.ops.app.ports.input.host_history_use_case import HostHistoryUseCase
from apps.ops.dependencies.ops_dependencies import (
    get_collector_tools_use_case,
    get_facility_use_case,
    get_host_history_use_case,
)

router = APIRouter(prefix="/admin/facility", tags=["admin"])


@router.get("/myself", response_model=ServiceCheckResponse)
def myself(use_case: FacilityUseCase = Depends(get_facility_use_case)) -> ServiceCheckResponse:
    return to_service_response(use_case.myself())


@router.get("/snapshot", response_model=FacilitySnapshotResponse, dependencies=[Depends(require_admin)])
def snapshot(use_case: FacilityUseCase = Depends(get_facility_use_case)) -> FacilitySnapshotResponse:
    return to_snapshot_response(use_case.snapshot())


@router.get("/history/myself", response_model=HostHistoryResponse)
def history_myself(use_case: HostHistoryUseCase = Depends(get_host_history_use_case)) -> HostHistoryResponse:
    return to_history_response(use_case.myself())


@router.get("/history", response_model=HostHistoryResponse, dependencies=[Depends(require_admin)])
def history(
    hours: Annotated[int, Query(), one_of(HOST_HISTORY_HOURS)] = 24,
    use_case: HostHistoryUseCase = Depends(get_host_history_use_case),
) -> HostHistoryResponse:
    return to_history_response(use_case.history(hours))


@router.get("/collectors/myself", response_model=CollectorLogResponse)
def collectors_myself(
    use_case: CollectorToolsUseCase = Depends(get_collector_tools_use_case),
) -> CollectorLogResponse:
    return to_log_response(use_case.myself())


# 로그에는 가린 뒤에도 내부 경로·오류가 남는다 — 운영 관리자만
@router.get("/collectors/{key}/log", response_model=CollectorLogResponse, dependencies=[Depends(require_operator)])
def collector_log(
    key: str,
    lines: int = Query(200, ge=10, le=1000),
    use_case: CollectorToolsUseCase = Depends(get_collector_tools_use_case),
) -> CollectorLogResponse:
    return to_log_response(use_case.log(key, lines))


@router.post("/collectors/{key}/run", response_model=CollectorRunResponse, status_code=202)
def collector_run(
    key: str,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: CollectorToolsUseCase = Depends(get_collector_tools_use_case),
) -> CollectorRunResponse:
    return to_run_response(use_case.run(key, to_actor(principal, client_ip_from_scope(request.scope))))
