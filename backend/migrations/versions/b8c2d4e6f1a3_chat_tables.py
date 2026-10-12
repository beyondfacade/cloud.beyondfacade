"""글로벌 채팅 — 메시지·읽음 표시 테이블

방(room)은 별도 테이블 없이 이름으로 구분한다: global(전체) · operators(관리자) · dm:{작은 id}:{큰 id}(1:1).
보낸 사람 이름·등급은 보낸 때 값을 그대로 남긴다 — 실시간 알림(NOTIFY) 본문만으로 화면을 그리기 위해.

Revision ID: b8c2d4e6f1a3
Revises: d7b3e5a9c214
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c2d4e6f1a3"
down_revision: Union[str, Sequence[str], None] = "d7b3e5a9c214"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_message",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("room", sa.String(40), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sender_username", sa.String(), nullable=False),
        sa.Column("sender_role", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reply_to_id", sa.BigInteger(), sa.ForeignKey("chat_message.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_chat_message_room_id", "chat_message", ["room", "id"])
    op.create_index("ix_chat_message_sender_created_at", "chat_message", ["sender_id", "created_at"])
    op.create_table(
        "chat_read",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("room", sa.String(40), primary_key=True),
        sa.Column("last_read_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chat_read")
    op.drop_index("ix_chat_message_sender_created_at", table_name="chat_message")
    op.drop_index("ix_chat_message_room_id", table_name="chat_message")
    op.drop_table("chat_message")
