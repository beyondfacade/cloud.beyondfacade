"""merge derived metrics and analysis-api heads

head가 둘이었던 이유: `feature/analysis-api`(SGIS 지오코딩·store 주소 컬럼 `b2c3d4e5f6a7`)와
`codex/seoul-atlas-landing`(commerce·neighborhood 적재, 파생 지표 `a4e7b2c9d813`)가 같은 부모
`e2a08b1e8f19` 아래서 따로 마이그레이션을 쌓았고, 공용 개발 DB에는 두 계보가 모두 적용돼
`alembic_version`에 행이 둘이었다. v0.23.0~v0.30.0은 그 사이 스크래치 임시 ini로 적용했다.
이 리비전은 DDL 없이 두 head를 하나로 묶는다 — T0-2 병합(2026-09-23).

Revision ID: c5d6e7f8a9b0
Revises: a4e7b2c9d813, b2c3d4e5f6a7
Create Date: 2026-09-23 22:34:35.901218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = ('a4e7b2c9d813', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
