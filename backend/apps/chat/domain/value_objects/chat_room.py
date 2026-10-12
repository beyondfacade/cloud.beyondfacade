"""채팅방 — 방 이름(key)만 보고 누가 들어갈 수 있는지 방 스스로 판단한다 (Strategy)."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMember:
    """채팅에 참여하는 로그인 회원."""

    id: int
    username: str
    can_operate: bool
    role: str = "viewer"  # 메시지에 남길 보낸 때의 등급 — 권한 판단은 can_operate로만


class ChatRoom(ABC):
    key: str
    kind: str

    @abstractmethod
    def admits(self, member: ChatMember) -> bool: ...

    @abstractmethod
    def title_for(self, member: ChatMember) -> str:
        """DM은 상대 이름을 알아야 해서 화면 제목을 바깥(interactor)에서 채운다 — 여기선 고정 방 이름만."""


@dataclass(frozen=True)
class GlobalRoom(ChatRoom):
    key: str = "global"
    kind: str = "global"

    def admits(self, member: ChatMember) -> bool:
        return True

    def title_for(self, member: ChatMember) -> str:
        return "전체"


@dataclass(frozen=True)
class OperatorRoom(ChatRoom):
    key: str = "operators"
    kind: str = "operators"

    def admits(self, member: ChatMember) -> bool:
        return member.can_operate

    def title_for(self, member: ChatMember) -> str:
        return "관리자"


@dataclass(frozen=True)
class DirectRoom(ChatRoom):
    low: int
    high: int
    kind: str = "direct"

    @property
    def key(self) -> str:  # type: ignore[override]
        return f"dm:{self.low}:{self.high}"

    def admits(self, member: ChatMember) -> bool:
        return member.id in (self.low, self.high)

    def title_for(self, member: ChatMember) -> str:
        return "대화"

    def partner_of(self, member_id: int) -> int:
        return self.high if member_id == self.low else self.low


_FIXED: dict[str, ChatRoom] = {room.key: room for room in (GlobalRoom(), OperatorRoom())}
_DIRECT = re.compile(r"^dm:([1-9]\d*):([1-9]\d*)$")


def direct_room(a: int, b: int) -> DirectRoom:
    if a == b:
        raise ValueError("자기 자신과는 대화방을 만들 수 없다")
    return DirectRoom(low=min(a, b), high=max(a, b))


def parse_room(key: str) -> ChatRoom:
    if key in _FIXED:
        return _FIXED[key]
    match = _DIRECT.match(key)
    if not match:
        raise ValueError(f"모르는 채팅방: {key}")
    low, high = int(match[1]), int(match[2])
    if low >= high:  # 같은 두 사람의 방이 이름 두 개를 갖지 않게 — 작은 번호가 앞
        raise ValueError(f"잘못된 대화방 이름: {key}")
    return DirectRoom(low=low, high=high)


def rooms_for(member: ChatMember) -> list[ChatRoom]:
    """DM을 뺀 고정 방 중 이 회원이 들어갈 수 있는 방."""
    return [room for room in _FIXED.values() if room.admits(member)]
