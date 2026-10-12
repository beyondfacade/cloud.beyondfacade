"""서버 프로세스 사이에 오가는 채팅 이벤트 JSON — Postgres NOTIFY 본문은 8000바이트 미만이어야 한다 (본문 500자면 충분히 작다)."""

import json
from dataclasses import asdict
from datetime import datetime

from apps.chat.app.dtos.chat_message_dto import ChatEventDto, ChatMessageDto, ChatReplyDto

CHANNEL = "chat_event"


def encode(event: ChatEventDto) -> str:
    return json.dumps(asdict(event), ensure_ascii=False, default=lambda value: value.isoformat())


def decode(payload: str) -> ChatEventDto:
    raw = json.loads(payload)
    message = raw.get("message")
    return ChatEventDto(
        type=raw["type"], room=raw["room"], message_id=raw["message_id"], message=_message(message) if message else None
    )


def _message(raw: dict) -> ChatMessageDto:
    reply = raw.get("reply_to")
    return ChatMessageDto(
        **{**raw, "created_at": datetime.fromisoformat(raw["created_at"]), "reply_to": ChatReplyDto(**reply) if reply else None}
    )
