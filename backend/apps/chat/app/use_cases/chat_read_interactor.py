from collections.abc import Callable
from datetime import UTC, datetime

from apps.chat.app.dtos.chat_read_dto import ChatReadDto
from apps.chat.app.ports.input.chat_read_use_case import ChatReadUseCase
from apps.chat.app.ports.output.chat_read_port import ChatReadRepositoryPort
from apps.chat.app.use_cases.room_access import admitted_room
from apps.chat.domain.value_objects.chat_room import ChatMember


class ChatReadInteractor(ChatReadUseCase):
    def __init__(
        self,
        reads: ChatReadRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._reads = reads
        self._clock = clock

    def myself(self) -> ChatReadDto:
        return ChatReadDto(room="global", last_read_id=0)

    def mark_read(self, member: ChatMember, room_key: str, last_read_id: int) -> ChatReadDto:
        room = admitted_room(member, room_key)
        stored = self._reads.advance(member.id, room.key, max(last_read_id, 0), self._clock())
        return ChatReadDto(room=room.key, last_read_id=stored)
