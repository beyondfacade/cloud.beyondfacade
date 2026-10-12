from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    body: str = Field(max_length=2000)  # 500자 규칙은 도메인이 판단 — 여기선 터무니없는 크기만 막는다
    reply_to_id: int | None = None


class ChatDirectRequest(BaseModel):
    user_id: int


class ChatConsultationRequest(BaseModel):
    expert_id: int
    hours: int


class ChatReplyResponse(BaseModel):
    id: int
    sender_username: str
    preview: str | None
    deleted: bool


class ChatMessageResponse(BaseModel):
    id: int
    room: str
    sender_id: int | None
    sender_username: str
    sender_role: str
    body: str | None
    deleted: bool
    created_at: datetime
    reply_to: ChatReplyResponse | None


class ChatPageResponse(BaseModel):
    items: list[ChatMessageResponse]
    has_more: bool


class ChatRoomResponse(BaseModel):
    key: str
    kind: str
    title: str
    partner_id: int | None
    unread: int
    last_message: ChatMessageResponse | None


class ChatExpertResponse(BaseModel):
    id: int
    username: str
    specialty: str | None
    hourly_rate: int | None
    status: Literal["available", "busy", "mine"]


class ChatEventResponse(BaseModel):
    type: str
    room: str
    message_id: int
    message: ChatMessageResponse | None
