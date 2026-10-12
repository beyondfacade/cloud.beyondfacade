import asyncio
from collections.abc import AsyncIterator
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.dependencies.admin_guard import require_admin, require_operator
from apps.chat.adapter.inbound.api.schemas.chat_message_schema import (
    ChatConsultationRequest,
    ChatDirectRequest,
    ChatExpertResponse,
    ChatMessageResponse,
    ChatPageResponse,
    ChatRoomResponse,
    ChatSendRequest,
)
from apps.chat.adapter.inbound.mappers.chat_message_mapper import (
    to_event_response,
    to_expert_response,
    to_member,
    to_message_response,
    to_page_response,
    to_room_response,
)
from apps.chat.app.dtos.chat_message_dto import ChatEventDto
from apps.chat.app.errors import InvalidChatAttachment
from apps.chat.app.ports.input.chat_message_use_case import ChatMessageUseCase
from apps.chat.dependencies.chat_dependencies import get_chat_message_use_case
from apps.chat.domain.services.chat_policy import MAX_ATTACHMENT_BYTES

router = APIRouter(prefix="/chat", tags=["chat"])

STREAM_LIFETIME_SECONDS = 50.0  # 배포 때 접속이 빨리 빠지고, 정지·로그아웃이 재접속 때 다시 검사되게
PING_SECONDS = 15.0
RETRY_MS = 3000


@router.get("/myself", response_model=ChatMessageResponse)
def myself(use_case: ChatMessageUseCase = Depends(get_chat_message_use_case)) -> ChatMessageResponse:
    return to_message_response(use_case.myself())


@router.get("/rooms", response_model=list[ChatRoomResponse])
def rooms(
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> list[ChatRoomResponse]:
    return [to_room_response(room) for room in use_case.rooms(to_member(principal))]


@router.get("/rooms/{room_key}/messages", response_model=ChatPageResponse)
def messages(
    room_key: str,
    before_id: int | None = Query(default=None, ge=1),
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> ChatPageResponse:
    return to_page_response(use_case.messages(to_member(principal), room_key, before_id))


@router.post("/rooms/{room_key}/messages", response_model=ChatMessageResponse, status_code=201)
def send(
    room_key: str,
    body: ChatSendRequest,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> ChatMessageResponse:
    return to_message_response(use_case.send(to_member(principal), room_key, body.body, body.reply_to_id))


@router.post("/rooms/{room_key}/attachments", response_model=ChatMessageResponse, status_code=201)
async def send_attachment(
    room_key: str,
    request: Request,
    name: str = Query(min_length=1, max_length=255),
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> ChatMessageResponse:
    """본문은 PDF 바이트 그대로(Content-Type: application/pdf) — multipart 의존성 없이 받는다."""
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_ATTACHMENT_BYTES:
        raise InvalidChatAttachment("5MB 이하 PDF 파일만 올릴 수 있어요.")
    content = await request.body()
    dto = await run_in_threadpool(use_case.send_attachment, to_member(principal), room_key, name, content)
    return to_message_response(dto)


@router.get("/messages/{message_id}/attachment", response_model=None)
def attachment(
    message_id: int,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> Response:
    name, content = use_case.attachment(to_member(principal), message_id)
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(name)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/messages/{message_id}", status_code=204)
def delete(
    message_id: int,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> Response:
    use_case.delete(to_member(principal), message_id)
    return Response(status_code=204)


@router.post("/direct", response_model=ChatRoomResponse)
def open_direct(
    body: ChatDirectRequest,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> ChatRoomResponse:
    return to_room_response(use_case.open_direct(to_member(principal), body.user_id))


@router.get("/members", response_model=list[ChatExpertResponse])
def members(
    q: str = Query(default="", max_length=50),
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> list[ChatExpertResponse]:
    return [to_expert_response(expert) for expert in use_case.search_members(to_member(principal), q)]


@router.post("/consultations", response_model=ChatRoomResponse, status_code=201)
def buy_consultation(
    body: ChatConsultationRequest,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> ChatRoomResponse:
    return to_room_response(use_case.buy_consultation(to_member(principal), body.expert_id, body.hours))


@router.get("/stream", response_model=None)
async def stream(
    request: Request,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: ChatMessageUseCase = Depends(get_chat_message_use_case),
) -> StreamingResponse:
    """볼 수 있는 모든 방의 새 메시지·삭제를 한 연결로 — 끊겼다 다시 붙으면 Last-Event-ID 다음부터 따라잡는다."""
    member = to_member(principal)
    last_event_id = _last_event_id(request.headers.get("last-event-id"))
    subscription = use_case.subscribe()  # 따라잡기 조회보다 먼저 구독해야 그 사이 메시지를 놓치지 않는다

    async def frames() -> AsyncIterator[str]:
        try:
            latest = await run_in_threadpool(use_case.latest_id)
            backlog = await run_in_threadpool(use_case.catch_up, member, last_event_id) if last_event_id else []
            sent = {event.message_id for event in backlog}
            for event in backlog:
                yield _frame(event)
            yield f"retry: {RETRY_MS}\nid: {max([latest, *sent])}\nevent: ready\ndata: {{}}\n\n"
            loop = asyncio.get_running_loop()
            deadline = loop.time() + STREAM_LIFETIME_SECONDS
            while (remaining := deadline - loop.time()) > 0:
                event = await subscription.next(min(PING_SECONDS, remaining))
                if event is None:
                    yield ": ping\n\n"
                elif use_case.visible(member, event) and not (event.type == "message" and event.message_id in sent):
                    yield _frame(event)
        finally:
            subscription.close()

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _last_event_id(raw: str | None) -> int | None:
    return int(raw) if raw and raw.isdigit() and int(raw) > 0 else None


def _frame(event: ChatEventDto) -> str:
    data = to_event_response(event).model_dump_json()
    event_id = f"id: {event.message_id}\n" if event.type == "message" else ""
    return f"{event_id}event: {event.type}\ndata: {data}\n\n"
