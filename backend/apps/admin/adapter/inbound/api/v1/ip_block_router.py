from fastapi import APIRouter, Depends, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.schemas.ip_block_schema import IpBlockCreateRequest, IpBlockResponse
from apps.admin.adapter.inbound.mappers.ip_block_mapper import to_response
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.dependencies.admin_dependencies import get_ip_block_use_case
from apps.admin.dependencies.admin_guard import require_admin, require_operator

router = APIRouter(prefix="/admin/security/ip-blocks", tags=["admin"])


@router.get("/myself", response_model=IpBlockResponse)
def myself(use_case: IpBlockUseCase = Depends(get_ip_block_use_case)) -> IpBlockResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[IpBlockResponse], dependencies=[Depends(require_admin)])
def list_active(use_case: IpBlockUseCase = Depends(get_ip_block_use_case)) -> list[IpBlockResponse]:
    return [to_response(dto) for dto in use_case.list_active()]


@router.post("", response_model=IpBlockResponse, status_code=201)
def block(
    body: IpBlockCreateRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: IpBlockUseCase = Depends(get_ip_block_use_case),
) -> IpBlockResponse:
    dto = use_case.block(body.ip, body.reason, body.ttl_minutes, principal, client_ip_from_scope(request.scope))
    return to_response(dto)


@router.delete("/{ip}", status_code=204)
def unblock(
    ip: str,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: IpBlockUseCase = Depends(get_ip_block_use_case),
) -> None:
    use_case.unblock(ip, principal, client_ip_from_scope(request.scope))
