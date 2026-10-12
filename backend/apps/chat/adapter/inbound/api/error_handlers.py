from fastapi import Request
from fastapi.responses import JSONResponse

from apps.chat.app.errors import (
    ChatError,
    ChatExpertBusy,
    ChatMemberNotFound,
    ChatMessageNotFound,
    ChatRoomForbidden,
    ChatRoomNotFound,
    ChatTooFast,
    InvalidChatAttachment,
    InvalidChatMessage,
    InvalidConsultation,
)

_STATUS: dict[type[ChatError], int] = {
    InvalidChatMessage: 400,
    InvalidChatAttachment: 400,
    InvalidConsultation: 400,
    ChatRoomForbidden: 403,
    ChatRoomNotFound: 404,
    ChatMessageNotFound: 404,
    ChatMemberNotFound: 404,
    ChatExpertBusy: 409,
    ChatTooFast: 429,
}


async def chat_error_handler(request: Request, error: ChatError) -> JSONResponse:
    return JSONResponse(
        status_code=_STATUS.get(type(error), 400),
        content={"error": {"code": error.code, "message": error.message}},
    )
