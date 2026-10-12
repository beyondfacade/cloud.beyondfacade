"""Driving Port — 글로벌 채팅 (전체 · 관리자 · 1:1). 로그인한 회원만 쓴다."""

from abc import ABC, abstractmethod

from apps.chat.app.dtos.chat_message_dto import (
    ChatEventDto,
    ChatMessageDto,
    ChatPageDto,
    ChatExpertDto,
    ChatRoomDto,
)
from apps.chat.app.ports.output.chat_message_port import ChatSubscription
from apps.chat.domain.value_objects.chat_room import ChatMember


class ChatMessageUseCase(ABC):
    @abstractmethod
    def myself(self) -> ChatMessageDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def rooms(self, member: ChatMember) -> list[ChatRoomDto]:
        """전체 → 관리자(관리자만) → 1:1(최근 대화순)."""

    @abstractmethod
    def messages(self, member: ChatMember, room_key: str, before_id: int | None) -> ChatPageDto: ...

    @abstractmethod
    def send(self, member: ChatMember, room_key: str, body: str, reply_to_id: int | None) -> ChatMessageDto:
        """InvalidChatMessage(1~500자) · ChatTooFast(10초에 5개) · ChatMessageNotFound(답장 대상)."""

    @abstractmethod
    def send_attachment(self, member: ChatMember, room_key: str, name: str, content: bytes) -> ChatMessageDto:
        """1:1 대화에만 PDF 한 개(5MB 이하, .pdf 이름, %PDF- 시작) — 본문은 파일 이름.
        1:1이 아니면 ChatRoomForbidden · 형식·크기가 틀리면 InvalidChatAttachment · 도배 제한은 메시지와 같다."""

    @abstractmethod
    def attachment(self, member: ChatMember, message_id: int) -> tuple[str, bytes]:
        """(파일 이름, PDF 바이트) — 그 방에 들어갈 수 있는 회원만, 지워진 메시지면 ChatMessageNotFound."""

    @abstractmethod
    def delete(self, member: ChatMember, message_id: int) -> None:
        """관리자 전용(라우터 가드) — 본문은 지우고 자리만 남긴다."""

    @abstractmethod
    def open_direct(self, member: ChatMember, user_id: int) -> ChatRoomDto:
        """1:1 대화방 — 일반 회원이 전문가에게만 건다(아니면 ChatRoomForbidden).
        다른 회원이 산 상담 중인 전문가면 ChatExpertBusy. 메시지가 오가기 전에는 방 목록에 없다."""

    @abstractmethod
    def search_members(self, member: ChatMember, q: str) -> list[ChatExpertDto]:
        """일반 회원에게만 전문가 목록(q가 비면 전체, 계정명순 50명)과 요금·상담 상태 — 그 밖의 등급은 빈 목록."""

    @abstractmethod
    def buy_consultation(self, member: ChatMember, expert_id: int, hours: int) -> ChatRoomDto:
        """더미 구매(결제 없음) — 지금부터 hours시간 그 전문가는 '대화 중'. 산 뒤 1:1 방을 돌려준다.
        일반 회원만(ChatRoomForbidden) · 1~3시간(InvalidConsultation) · 이미 상담 중이면 ChatExpertBusy."""

    @abstractmethod
    def reset_demo_consultations(self, username: str) -> None:
        """로컬 시연 계정(001)이 로그아웃하면 시연 전문가(002~005)의 상담을 초기 상태로, 1:1 대화 내역은 비운다 — 그 밖의 계정은 아무 일도 없다."""

    @abstractmethod
    def latest_id(self) -> int: ...

    @abstractmethod
    def catch_up(self, member: ChatMember, after_id: int) -> list[ChatEventDto]:
        """재접속 사이에 놓친, 볼 수 있는 방의 메시지."""

    @abstractmethod
    def subscribe(self) -> ChatSubscription: ...

    @abstractmethod
    def visible(self, member: ChatMember, event: ChatEventDto) -> bool: ...
