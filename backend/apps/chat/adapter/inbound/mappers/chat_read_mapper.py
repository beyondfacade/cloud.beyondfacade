"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.chat.adapter.inbound.api.schemas.chat_read_schema import ChatReadResponse
from apps.chat.app.dtos.chat_read_dto import ChatReadDto


def to_response(dto: ChatReadDto) -> ChatReadResponse:
    return ChatReadResponse(**asdict(dto))
