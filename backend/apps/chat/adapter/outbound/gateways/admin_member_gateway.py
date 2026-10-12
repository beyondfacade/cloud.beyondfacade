"""Driven Adapter — 채팅 상대는 admin BC의 회원 계정 (cross-BC 접근은 이 파일 안에서만)."""

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.chat.app.dtos.chat_message_dto import ChatPeerDto
from apps.chat.app.ports.output.chat_message_port import ChatMemberPort


def _peer(principal: AdminPrincipalDto) -> ChatPeerDto:
    return ChatPeerDto(
        id=principal.id,
        username=principal.username,
        role=principal.role,
        hourly_rate=principal.hourly_rate,
        specialty=principal.specialty,
        avatar_version=principal.avatar_version,
    )


class AdminMemberGateway(ChatMemberPort):
    def __init__(self, users: AdminUserUseCase) -> None:
        self._users = users

    def search(self, q: str, exclude_id: int, limit: int, role: str) -> list[ChatPeerDto]:
        return [_peer(p) for p in self._users.search_members(q, exclude_id, limit, role)]

    def active(self, user_id: int) -> ChatPeerDto | None:
        principal = self._users.active_member(user_id)
        return _peer(principal) if principal else None

    def members(self, user_ids: list[int]) -> dict[int, ChatPeerDto]:
        return {user_id: _peer(p) for user_id, p in self._users.members_by_ids(user_ids).items()}
