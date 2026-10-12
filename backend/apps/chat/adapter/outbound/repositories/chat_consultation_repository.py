from dataclasses import replace
from datetime import datetime

from sqlalchemy import select

from apps.chat.adapter.outbound.orms.chat_consultation_orm import ChatConsultationOrm
from apps.chat.app.ports.output.chat_consultation_port import ChatConsultationRepositoryPort
from apps.chat.domain.entities.chat_consultation_entity import ChatConsultation
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyChatConsultationRepository(ChatConsultationRepositoryPort):
    def add(self, consultation: ChatConsultation) -> ChatConsultation:
        orm = ChatConsultationOrm(
            viewer_id=consultation.viewer_id,
            expert_id=consultation.expert_id,
            hours=consultation.hours,
            price=consultation.price,
            started_at=consultation.started_at,
            ends_at=consultation.ends_at,
        )
        with session_scope() as session:
            session.add(orm)
            session.flush()
            return replace(consultation, id=orm.id)

    def holders(self, now: datetime) -> dict[int, int]:
        query = (
            select(ChatConsultationOrm.expert_id, ChatConsultationOrm.viewer_id)
            .where(ChatConsultationOrm.started_at <= now, ChatConsultationOrm.ends_at > now)
            .order_by(ChatConsultationOrm.id)
        )
        with session_scope() as session:
            return {expert_id: viewer_id for expert_id, viewer_id in session.execute(query)}
