from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    room: str
    sender_id: int | None  # 계정이 지워지면 비지만 보낼 때의 이름·등급은 남는다
    sender_username: str
    sender_role: str
    body: str
    created_at: datetime
    reply_to_id: int | None = None
    deleted_at: datetime | None = None
    deleted_by: int | None = None
    attachment_name: str | None = None  # PDF 첨부 메시지면 파일 이름 (본문도 같은 이름)
    attachment_size: int | None = None
    id: int | None = None

    @property
    def deleted(self) -> bool:
        return self.deleted_at is not None
