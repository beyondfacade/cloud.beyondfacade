"""Driven Port — 메시지 저장소 · 실시간 발행/구독 · 회원 조회 (역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.chat.app.dtos.chat_message_dto import ChatEventDto, ChatPeerDto
from apps.chat.domain.entities.chat_message_entity import ChatMessage


class ChatMessageRepositoryPort(ABC):
    @abstractmethod
    def add(self, message: ChatMessage, attachment: bytes | None = None) -> ChatMessage:
        """attachment가 있으면 메시지와 같은 트랜잭션에 PDF 바이트를 저장한다."""

    @abstractmethod
    def attachment_content(self, message_id: int) -> bytes | None: ...

    @abstractmethod
    def get(self, message_id: int) -> ChatMessage | None: ...

    @abstractmethod
    def get_many(self, message_ids: list[int]) -> dict[int, ChatMessage]: ...

    @abstractmethod
    def page(self, room: str, before_id: int | None, limit: int) -> list[ChatMessage]:
        """before_id보다 앞선 최신 limit개 — 오래된 것 → 최신 순으로 돌려준다."""

    @abstractmethod
    def after(self, rooms: list[str], after_id: int, limit: int) -> list[ChatMessage]:
        """재접속 따라잡기 — after_id 다음부터 오래된 순 limit개."""

    @abstractmethod
    def latest(self, room: str) -> ChatMessage | None: ...

    @abstractmethod
    def latest_id(self) -> int:
        """모든 방을 통틀어 가장 최근 메시지 id — 없으면 0."""

    @abstractmethod
    def count_by_sender_since(self, sender_id: int, since: datetime) -> int: ...

    @abstractmethod
    def count_unread(self, room: str, after_id: int, reader_id: int) -> int:
        """after_id 다음 메시지 중 남이 보낸, 지워지지 않은 것."""

    @abstractmethod
    def direct_rooms_of(self, user_id: int) -> list[str]:
        """메시지가 한 번이라도 오간 1:1 대화방 키."""

    @abstractmethod
    def mark_deleted(self, message_id: int, by: int, at: datetime) -> ChatMessage: ...

    @abstractmethod
    def delete_rooms(self, rooms: list[str]) -> None:
        """방의 메시지를 첨부까지 실제로 지운다 — 시연 초기화 전용."""


class ChatSubscription(ABC):
    @abstractmethod
    async def next(self, timeout: float) -> ChatEventDto | None:
        """timeout초 안에 온 이벤트 — 없으면 None."""

    @abstractmethod
    def close(self) -> None: ...


class ChatEventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: ChatEventDto) -> None:
        """모든 서버 프로세스의 구독자에게 — 같은 프로세스도 이 경로로 받는다."""


class ChatEventFeedPort(ABC):
    @abstractmethod
    def subscribe(self) -> ChatSubscription: ...


class ChatMemberPort(ABC):
    @abstractmethod
    def search(self, q: str, exclude_id: int, limit: int, role: str) -> list[ChatPeerDto]: ...

    @abstractmethod
    def active(self, user_id: int) -> ChatPeerDto | None: ...

    @abstractmethod
    def usernames(self, user_ids: list[int]) -> dict[int, str]: ...
