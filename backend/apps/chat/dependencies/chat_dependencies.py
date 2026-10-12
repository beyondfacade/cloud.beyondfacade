"""Composition Root (DIP) — chat BC Port에 Adapter를 주입한다."""

from functools import cache

from fastapi import Depends
from sqlalchemy import make_url

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.chat.adapter.outbound.gateways.admin_member_gateway import AdminMemberGateway
from apps.chat.adapter.outbound.gateways.pg_listen_chat_feed import PgListenChatFeed
from apps.chat.adapter.outbound.gateways.pg_notify_chat_publisher import PgNotifyChatPublisher
from apps.chat.adapter.outbound.repositories.chat_message_repository import SqlAlchemyChatMessageRepository
from apps.chat.adapter.outbound.repositories.chat_read_repository import SqlAlchemyChatReadRepository
from apps.chat.app.ports.input.chat_message_use_case import ChatMessageUseCase
from apps.chat.app.ports.input.chat_read_use_case import ChatReadUseCase
from apps.chat.app.ports.output.chat_message_port import ChatEventFeedPort, ChatEventPublisherPort
from apps.chat.app.use_cases.chat_message_interactor import ChatMessageInteractor
from apps.chat.app.use_cases.chat_read_interactor import ChatReadInteractor
from core.matrix.grid_keymaker_secret_manager import get_settings


@cache
def get_chat_event_feed() -> ChatEventFeedPort:
    """프로세스당 하나 — LISTEN 연결을 접속자마다 열지 않는다."""
    url = make_url(get_settings().database_url).set(drivername="postgresql")
    return PgListenChatFeed(url.render_as_string(hide_password=False))


def get_chat_event_publisher() -> ChatEventPublisherPort:
    return PgNotifyChatPublisher()


def get_chat_message_use_case(
    publisher: ChatEventPublisherPort = Depends(get_chat_event_publisher),
    feed: ChatEventFeedPort = Depends(get_chat_event_feed),
) -> ChatMessageUseCase:
    return ChatMessageInteractor(
        messages=SqlAlchemyChatMessageRepository(),
        reads=SqlAlchemyChatReadRepository(),
        members=AdminMemberGateway(get_admin_user_use_case()),
        publisher=publisher,
        feed=feed,
    )


def get_chat_read_use_case() -> ChatReadUseCase:
    return ChatReadInteractor(reads=SqlAlchemyChatReadRepository())
