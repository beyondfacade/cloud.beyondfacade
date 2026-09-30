"""공개 회원가입·구글 로그인 — admin_user에 이메일·구글 식별자, 비밀번호는 선택

Revision ID: 7b1d4e9a2c60
Revises: 5e8a3c1d9f27
Create Date: 2026-09-30 10:40:00.000000

구글로만 가입한 계정은 비밀번호가 없다(password_hash NULL). 이메일은 소문자로 맞춰 저장한다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b1d4e9a2c60"
down_revision: Union[str, Sequence[str], None] = "5e8a3c1d9f27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_user", sa.Column("email", sa.String(), nullable=True))
    op.add_column("admin_user", sa.Column("google_sub", sa.String(), nullable=True))
    op.create_unique_constraint("uq_admin_user_email", "admin_user", ["email"])
    op.create_unique_constraint("uq_admin_user_google_sub", "admin_user", ["google_sub"])
    op.alter_column("admin_user", "password_hash", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.execute("delete from admin_user where password_hash is null")
    op.alter_column("admin_user", "password_hash", existing_type=sa.String(), nullable=False)
    op.drop_constraint("uq_admin_user_google_sub", "admin_user", type_="unique")
    op.drop_constraint("uq_admin_user_email", "admin_user", type_="unique")
    op.drop_column("admin_user", "google_sub")
    op.drop_column("admin_user", "email")
