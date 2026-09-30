from fastapi import APIRouter, Depends

from apps.admin.dependencies.admin_guard import require_admin, require_operator
from apps.ops.adapter.inbound.api.schemas.healthcare_schema import (
    HealthcareSnapshotResponse,
    LlmRouteResponse,
    ProbeRequest,
    ProbeResultResponse,
)
from apps.ops.adapter.inbound.mappers.healthcare_mapper import (
    to_probe_response,
    to_route_response,
    to_snapshot_response,
)
from apps.ops.app.ports.input.healthcare_use_case import HealthcareUseCase
from apps.ops.dependencies.ops_dependencies import get_healthcare_use_case

router = APIRouter(prefix="/admin/healthcare", tags=["admin"])


@router.get("/myself", response_model=LlmRouteResponse)
def myself(use_case: HealthcareUseCase = Depends(get_healthcare_use_case)) -> LlmRouteResponse:
    return to_route_response(use_case.myself())


@router.get("/snapshot", response_model=HealthcareSnapshotResponse, dependencies=[Depends(require_admin)])
def snapshot(use_case: HealthcareUseCase = Depends(get_healthcare_use_case)) -> HealthcareSnapshotResponse:
    return to_snapshot_response(use_case.snapshot())


# 프로브는 실제 LLM 호출(토큰 비용)이 나가므로 운영 관리자만
@router.post("/probe", response_model=ProbeResultResponse, dependencies=[Depends(require_operator)])
def probe(body: ProbeRequest, use_case: HealthcareUseCase = Depends(get_healthcare_use_case)) -> ProbeResultResponse:
    return to_probe_response(use_case.probe(body.kind, body.message))
