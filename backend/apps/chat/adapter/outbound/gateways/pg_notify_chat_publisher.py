"""Driven Adapter — Postgres NOTIFY로 발행. 서버가 여러 대여도 같은 DB를 LISTEN하는 모든 프로세스가 받는다."""

from sqlalchemy import text

from apps.chat.adapter.outbound.gateways.chat_event_codec import CHANNEL, encode
from apps.chat.app.dtos.chat_message_dto import ChatEventDto
from apps.chat.app.ports.output.chat_message_port import ChatEventPublisherPort
from core.matrix.grid_oracle_database_manager import session_scope


class PgNotifyChatPublisher(ChatEventPublisherPort):
    def publish(self, event: ChatEventDto) -> None:
        with session_scope() as session:
            session.execute(text("select pg_notify(:channel, :payload)"), {"channel": CHANNEL, "payload": encode(event)})
