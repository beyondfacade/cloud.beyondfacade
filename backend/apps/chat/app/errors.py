"""chat BC 애플리케이션 오류 — HTTP 상태 매핑은 inbound 어댑터(error_handlers)가 한다."""


class ChatError(Exception):
    code = "CHAT_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ChatRoomNotFound(ChatError):
    code = "CHAT_ROOM_NOT_FOUND"


class ChatRoomForbidden(ChatError):
    code = "CHAT_ROOM_FORBIDDEN"


class InvalidChatMessage(ChatError):
    code = "INVALID_CHAT_MESSAGE"


class ChatTooFast(ChatError):
    code = "CHAT_TOO_FAST"


class ChatMessageNotFound(ChatError):
    code = "CHAT_MESSAGE_NOT_FOUND"


class ChatMemberNotFound(ChatError):
    code = "CHAT_MEMBER_NOT_FOUND"
