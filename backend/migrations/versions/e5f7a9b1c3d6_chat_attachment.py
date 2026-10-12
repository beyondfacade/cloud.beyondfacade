"""1:1 대화 PDF 첨부 — chat_message.attachment_name/size + chat_attachment(바이트)

Revision ID: e5f7a9b1c3d6
Revises: d4e6f8a1b3c5
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f7a9b1c3d6"
down_revision: Union[str, Sequence[str], None] = "d4e6f8a1b3c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_message", sa.Column("attachment_name", sa.String(length=120), nullable=True))
    op.add_column("chat_message", sa.Column("attachment_size", sa.Integer(), nullable=True))
    op.create_table(
        "chat_attachment",
        sa.Column("message_id", sa.BigInteger(), sa.ForeignKey("chat_message.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chat_attachment")
    op.drop_column("chat_message", "attachment_size")
    op.drop_column("chat_message", "attachment_name")
