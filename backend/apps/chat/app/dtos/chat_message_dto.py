from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatReplyDto:
    id: int
    sender_username: str
    preview: str | None  # 지워진 메시지면 None
    deleted: bool


@dataclass(frozen=True)
class ChatAttachmentDto:
    name: str
    size: int  # bytes


@dataclass(frozen=True)
class ChatMessageDto:
    id: int
    room: str
    sender_id: int | None
    sender_username: str
    sender_role: str
    body: str | None  # 지워진 메시지면 None — 본문은 API 밖으로 내보내지 않는다
    deleted: bool
    created_at: datetime
    reply_to: ChatReplyDto | None
    attachment: ChatAttachmentDto | None = None  # 지워진 메시지면 None
    sender_avatar_version: int | None = None  # 보낸 사람의 지금 프로필 사진 버전 — 없으면 None


@dataclass(frozen=True)
class ChatPageDto:
    items: list[ChatMessageDto]  # 오래된 것 → 최신
    has_more: bool


@dataclass(frozen=True)
class ChatRoomDto:
    key: str
    kind: str
    title: str
    partner_id: int | None
    partner_avatar_version: int | None  # 상대 프로필 사진 버전 — 없으면 None
    unread: int
    last_message: ChatMessageDto | None


@dataclass(frozen=True)
class ChatPeerDto:
    id: int
    username: str
    role: str
    hourly_rate: int | None
    specialty: str | None
    avatar_version: int | None


@dataclass(frozen=True)
class ChatExpertDto:
    id: int
    username: str
    specialty: str | None
    hourly_rate: int | None
    status: str  # available | busy | mine
    avatar_version: int | None


@dataclass(frozen=True)
class ChatEventDto:
    type: str  # message | deleted
    room: str
    message_id: int
    message: ChatMessageDto | None  # deleted면 None
