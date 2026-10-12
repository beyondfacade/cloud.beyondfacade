from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from apps.chat.adapter.outbound.orms.chat_read_orm import ChatReadOrm
from apps.chat.app.ports.output.chat_read_port import ChatReadRepositoryPort
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyChatReadRepository(ChatReadRepositoryPort):
    def last_read_ids(self, user_id: int) -> dict[str, int]:
        query = select(ChatReadOrm.room, ChatReadOrm.last_read_id).where(ChatReadOrm.user_id == user_id)
        with session_scope() as session:
            return {room: last_read_id for room, last_read_id in session.execute(query)}

    def advance(self, user_id: int, room: str, last_read_id: int, at: datetime) -> int:
        statement = insert(ChatReadOrm).values(user_id=user_id, room=room, last_read_id=last_read_id, updated_at=at)
        statement = statement.on_conflict_do_update(
            index_elements=[ChatReadOrm.user_id, ChatReadOrm.room],
            set_={
                "last_read_id": func.greatest(ChatReadOrm.last_read_id, statement.excluded.last_read_id),
                "updated_at": statement.excluded.updated_at,
            },
        ).returning(ChatReadOrm.last_read_id)
        with session_scope() as session:
            return session.execute(statement).scalar_one()
