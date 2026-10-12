from fastapi import APIRouter, Depends

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.dependencies.admin_guard import require_admin
from apps.chat.adapter.inbound.api.schemas.chat_read_schema import ChatReadRequest, ChatReadResponse
from apps.chat.adapter.inbound.mappers.chat_message_mapper import to_member
from apps.chat.adapter.inbound.mappers.chat_read_mapper import to_response
from apps.chat.app.ports.input.chat_read_use_case import ChatReadUseCase
from apps.chat.dependencies.chat_dependencies import get_chat_read_use_case

router = APIRouter(prefix="/chat/reads", tags=["chat"])


@router.get("/myself", response_model=ChatReadResponse)
def myself(use_case: ChatReadUseCase = Depends(get_chat_read_use_case)) -> ChatReadResponse:
    return to_response(use_case.myself())


@router.put("/{room_key}", response_model=ChatReadResponse)
def mark_read(
    room_key: str,
    body: ChatReadRequest,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatReadUseCase = Depends(get_chat_read_use_case),
) -> ChatReadResponse:
    return to_response(use_case.mark_read(to_member(principal), room_key, body.last_read_id))
