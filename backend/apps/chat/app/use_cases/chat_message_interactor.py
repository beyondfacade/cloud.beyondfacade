from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apps.chat.app.dtos.chat_message_dto import (
    ChatEventDto,
    ChatExpertDto,
    ChatMessageDto,
    ChatPageDto,
    ChatReplyDto,
    ChatRoomDto,
)
from apps.chat.app.errors import (
    ChatExpertBusy,
    ChatMemberNotFound,
    ChatMessageNotFound,
    ChatRoomForbidden,
    ChatTooFast,
    InvalidChatMessage,
    InvalidConsultation,
)
from apps.chat.app.ports.input.chat_message_use_case import ChatMessageUseCase
from apps.chat.app.ports.output.chat_consultation_port import ChatConsultationRepositoryPort
from apps.chat.app.ports.output.chat_message_port import (
    ChatEventFeedPort,
    ChatEventPublisherPort,
    ChatMemberPort,
    ChatMessageRepositoryPort,
    ChatSubscription,
)
from apps.chat.app.ports.output.chat_read_port import ChatReadRepositoryPort
from apps.chat.app.use_cases.room_access import admitted_room
from apps.chat.domain.entities.chat_consultation_entity import ChatConsultation
from apps.chat.domain.entities.chat_message_entity import ChatMessage
from apps.chat.domain.services.chat_policy import (
    CONSULTATION_HOURS,
    DIRECT_OPENER_ROLE,
    DIRECT_PARTNER_ROLE,
    RATE_LIMIT_COUNT,
    can_open_direct,
    can_talk_direct,
    clean_body,
    expert_status,
    rate_window_start,
    reply_preview,
)
from apps.chat.domain.value_objects.chat_room import (
    ChatMember,
    ChatRoom,
    DirectRoom,
    direct_room,
    parse_room,
    rooms_for,
)

PAGE_SIZE = 50
CATCH_UP_LIMIT = 200
MEMBER_SEARCH_LIMIT = 50
# 로컬 시연 계정 — 001이 로그아웃하면 002~005의 상담을 지우고 '001이 003을 1시간 산 상태'로 되돌린다
DEMO_VIEWER = "001"
DEMO_EXPERTS = ("002", "003", "004", "005")
DEMO_BUSY_EXPERT = "003"
DEMO_HOURS = 1


def _reply_dto(message: ChatMessage) -> ChatReplyDto:
    return ChatReplyDto(
        id=message.id,
        sender_username=message.sender_username,
        preview=None if message.deleted else reply_preview(message.body),
        deleted=message.deleted,
    )


def to_message_dto(message: ChatMessage, replies: dict[int, ChatMessage]) -> ChatMessageDto:
    replied = replies.get(message.reply_to_id) if message.reply_to_id else None
    return ChatMessageDto(
        id=message.id,
        room=message.room,
        sender_id=message.sender_id,
        sender_username=message.sender_username,
        sender_role=message.sender_role,
        body=None if message.deleted else message.body,
        deleted=message.deleted,
        created_at=message.created_at,
        reply_to=_reply_dto(replied) if replied else None,
    )


class ChatMessageInteractor(ChatMessageUseCase):
    def __init__(
        self,
        messages: ChatMessageRepositoryPort,
        reads: ChatReadRepositoryPort,
        members: ChatMemberPort,
        consultations: ChatConsultationRepositoryPort,
        publisher: ChatEventPublisherPort,
        feed: ChatEventFeedPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._messages = messages
        self._reads = reads
        self._members = members
        self._consultations = consultations
        self._publisher = publisher
        self._feed = feed
        self._clock = clock

    def myself(self) -> ChatMessageDto:
        return ChatMessageDto(
            id=1, room="global", sender_id=1, sender_username="myself", sender_role="viewer", body="myself",
            deleted=False, created_at=datetime(2026, 9, 30, tzinfo=UTC), reply_to=None,
        )

    def rooms(self, member: ChatMember) -> list[ChatRoomDto]:
        reads = self._reads.last_read_ids(member.id)
        fixed = [self._summary(member, room, room.title_for(member), None, reads) for room in rooms_for(member)]
        directs = [room for key in self._messages.direct_rooms_of(member.id) if isinstance(room := parse_room(key), DirectRoom)]
        names = self._members.usernames([room.partner_of(member.id) for room in directs])
        direct_summaries = [
            self._summary(member, room, names.get(room.partner_of(member.id), "알 수 없음"), room.partner_of(member.id), reads)
            for room in directs
        ]
        direct_summaries.sort(key=lambda room: room.last_message.id if room.last_message else 0, reverse=True)
        return fixed + direct_summaries

    def messages(self, member: ChatMember, room_key: str, before_id: int | None) -> ChatPageDto:
        room = admitted_room(member, room_key)
        found = self._messages.page(room.key, before_id, PAGE_SIZE + 1)
        has_more = len(found) > PAGE_SIZE
        return ChatPageDto(items=self._dtos(found[-PAGE_SIZE:]), has_more=has_more)

    def send(self, member: ChatMember, room_key: str, body: str, reply_to_id: int | None) -> ChatMessageDto:
        room = admitted_room(member, room_key)
        if isinstance(room, DirectRoom):
            partner = self._members.active(room.partner_of(member.id))
            if partner is None:
                raise ChatMemberNotFound("대화 상대를 찾을 수 없습니다.")
            if not can_talk_direct(member.role, partner.role):
                raise ChatRoomForbidden("1:1 대화는 일반 회원과 전문가 사이에서만 할 수 있습니다.")
        text = clean_body(body)
        if text is None:
            raise InvalidChatMessage("메시지는 1~500자로 입력해 주세요.")
        now = self._clock()
        if self._messages.count_by_sender_since(member.id, rate_window_start(now)) >= RATE_LIMIT_COUNT:
            raise ChatTooFast("메시지를 너무 빨리 보내고 있어요. 잠시 후 다시 보내 주세요.")
        replies = self._reply_target(room, reply_to_id)
        saved = self._messages.add(
            ChatMessage(
                room=room.key, sender_id=member.id, sender_username=member.username, sender_role=member.role,
                body=text, created_at=now, reply_to_id=reply_to_id,
            )
        )
        dto = to_message_dto(saved, replies)
        self._publisher.publish(ChatEventDto(type="message", room=room.key, message_id=saved.id, message=dto))
        return dto

    def delete(self, member: ChatMember, message_id: int) -> None:
        message = self._messages.get(message_id)
        if message is None or not parse_room(message.room).admits(member):
            raise ChatMessageNotFound("메시지를 찾을 수 없습니다.")
        if message.deleted:
            return
        self._messages.mark_deleted(message_id, member.id, self._clock())
        self._publisher.publish(ChatEventDto(type="deleted", room=message.room, message_id=message_id, message=None))

    def open_direct(self, member: ChatMember, user_id: int) -> ChatRoomDto:
        peer = self._members.active(user_id) if user_id != member.id else None
        if peer is None:
            raise ChatMemberNotFound("대화 상대를 찾을 수 없습니다.")
        if not can_open_direct(member.role, peer.role):
            raise ChatRoomForbidden("1:1 대화는 일반 회원이 전문가에게만 걸 수 있습니다.")
        if expert_status(peer.id, member.id, self._consultations.holders(self._clock())) == "busy":
            raise ChatExpertBusy("이 전문가는 지금 다른 회원과 상담 중입니다.")
        room = direct_room(member.id, peer.id)
        return self._summary(member, room, peer.username, peer.id, self._reads.last_read_ids(member.id))

    def search_members(self, member: ChatMember, q: str) -> list[ChatExpertDto]:
        if member.role != DIRECT_OPENER_ROLE:
            return []
        holders = self._consultations.holders(self._clock())
        return [
            ChatExpertDto(
                id=peer.id,
                username=peer.username,
                specialty=peer.specialty,
                hourly_rate=peer.hourly_rate,
                status=expert_status(peer.id, member.id, holders),
            )
            for peer in self._members.search(q.strip(), member.id, MEMBER_SEARCH_LIMIT, DIRECT_PARTNER_ROLE)
        ]

    def buy_consultation(self, member: ChatMember, expert_id: int, hours: int) -> ChatRoomDto:
        if member.role != DIRECT_OPENER_ROLE:
            raise ChatRoomForbidden("상담은 일반 회원만 살 수 있습니다.")
        if hours not in CONSULTATION_HOURS:
            raise InvalidConsultation("상담 시간은 1~3시간 중에서 골라 주세요.")
        expert = self._members.active(expert_id)
        if expert is None or expert.role != DIRECT_PARTNER_ROLE:
            raise ChatMemberNotFound("전문가를 찾을 수 없습니다.")
        if expert.hourly_rate is None:
            raise InvalidConsultation("요금이 정해지지 않은 전문가입니다.")
        now = self._clock()
        if expert.id in self._consultations.holders(now):
            raise ChatExpertBusy("이 전문가는 지금 상담 중입니다.")
        self._consultations.add(
            ChatConsultation(
                viewer_id=member.id, expert_id=expert.id, hours=hours, price=expert.hourly_rate * hours,
                started_at=now, ends_at=now + timedelta(hours=hours),
            )
        )
        return self.open_direct(member, expert.id)

    def reset_demo_consultations(self, username: str) -> None:
        if username != DEMO_VIEWER:
            return
        viewers = self._members.search(DEMO_VIEWER, 0, MEMBER_SEARCH_LIMIT, DIRECT_OPENER_ROLE)
        viewer = next((peer for peer in viewers if peer.username == DEMO_VIEWER), None)
        experts = {
            peer.username: peer
            for peer in self._members.search("", 0, MEMBER_SEARCH_LIMIT, DIRECT_PARTNER_ROLE)
            if peer.username in DEMO_EXPERTS
        }
        self._consultations.delete_for_experts([peer.id for peer in experts.values()])
        busy = experts.get(DEMO_BUSY_EXPERT)
        if viewer is None or busy is None or busy.hourly_rate is None:
            return
        now = self._clock()
        self._consultations.add(
            ChatConsultation(
                viewer_id=viewer.id, expert_id=busy.id, hours=DEMO_HOURS, price=busy.hourly_rate * DEMO_HOURS,
                started_at=now, ends_at=now + timedelta(hours=DEMO_HOURS),
            )
        )

    def latest_id(self) -> int:
        return self._messages.latest_id()

    def catch_up(self, member: ChatMember, after_id: int) -> list[ChatEventDto]:
        keys = [room.key for room in rooms_for(member)] + self._messages.direct_rooms_of(member.id)
        found = self._messages.after(keys, after_id, CATCH_UP_LIMIT)
        return [
            ChatEventDto(type="message", room=dto.room, message_id=dto.id, message=dto) for dto in self._dtos(found)
        ]

    def subscribe(self) -> ChatSubscription:
        return self._feed.subscribe()

    def visible(self, member: ChatMember, event: ChatEventDto) -> bool:
        try:
            return parse_room(event.room).admits(member)
        except ValueError:
            return False

    def _reply_target(self, room: ChatRoom, reply_to_id: int | None) -> dict[int, ChatMessage]:
        if reply_to_id is None:
            return {}
        replied = self._messages.get(reply_to_id)
        if replied is None or replied.room != room.key:
            raise ChatMessageNotFound("답장할 메시지를 찾을 수 없습니다.")
        return {replied.id: replied}

    def _dtos(self, found: list[ChatMessage]) -> list[ChatMessageDto]:
        replies = self._messages.get_many([m.reply_to_id for m in found if m.reply_to_id])
        return [to_message_dto(message, replies) for message in found]

    def _summary(
        self, member: ChatMember, room: ChatRoom, title: str, partner_id: int | None, reads: dict[str, int]
    ) -> ChatRoomDto:
        last = self._messages.latest(room.key)
        return ChatRoomDto(
            key=room.key,
            kind=room.kind,
            title=title,
            partner_id=partner_id,
            unread=self._messages.count_unread(room.key, reads.get(room.key, 0), member.id),
            last_message=to_message_dto(last, self._messages.get_many([last.reply_to_id] if last.reply_to_id else []))
            if last
            else None,
        )
