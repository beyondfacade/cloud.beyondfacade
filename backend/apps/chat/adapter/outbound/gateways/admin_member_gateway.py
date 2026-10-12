"""Driven Adapter — 채팅 상대는 admin BC의 회원 계정 (cross-BC 접근은 이 파일 안에서만)."""

from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.chat.app.dtos.chat_message_dto import ChatPeerDto
from apps.chat.app.ports.output.chat_message_port import ChatMemberPort


class AdminMemberGateway(ChatMemberPort):
    def __init__(self, users: AdminUserUseCase) -> None:
        self._users = users

    def search(self, q: str, exclude_id: int, limit: int) -> list[ChatPeerDto]:
        return [ChatPeerDto(id=p.id, username=p.username) for p in self._users.search_members(q, exclude_id, limit)]

    def active(self, user_id: int) -> ChatPeerDto | None:
        principal = self._users.active_member(user_id)
        return ChatPeerDto(id=principal.id, username=principal.username) if principal else None

    def usernames(self, user_ids: list[int]) -> dict[int, str]:
        return {user_id: p.username for user_id, p in self._users.members_by_ids(user_ids).items()}

    def expert(self, exclude_id: int) -> ChatPeerDto | None:
        principal = self._users.first_active_expert(exclude_id)
        return ChatPeerDto(id=principal.id, username=principal.username) if principal else None
