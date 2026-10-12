"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.chat.adapter.inbound.api.schemas.chat_message_schema import (
    ChatEventResponse,
    ChatMessageResponse,
    ChatPageResponse,
    ChatExpertResponse,
    ChatRoomResponse,
)
from apps.chat.app.dtos.chat_message_dto import ChatEventDto, ChatExpertDto, ChatMessageDto, ChatPageDto, ChatRoomDto
from apps.chat.domain.value_objects.chat_room import ChatMember


def to_member(principal: AdminPrincipalDto) -> ChatMember:
    return ChatMember(
        id=principal.id,
        username=principal.username,
        can_operate=principal.can_operate,
        role=principal.role,
        avatar_version=principal.avatar_version,
    )


def to_message_response(dto: ChatMessageDto) -> ChatMessageResponse:
    return ChatMessageResponse(**asdict(dto))


def to_page_response(dto: ChatPageDto) -> ChatPageResponse:
    return ChatPageResponse(**asdict(dto))


def to_room_response(dto: ChatRoomDto) -> ChatRoomResponse:
    return ChatRoomResponse(**asdict(dto))


def to_expert_response(dto: ChatExpertDto) -> ChatExpertResponse:
    return ChatExpertResponse(**asdict(dto))


def to_event_response(dto: ChatEventDto) -> ChatEventResponse:
    return ChatEventResponse(**asdict(dto))
