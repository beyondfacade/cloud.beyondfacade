"""region_commerce_sales_breakdown table

Revision ID: d8b5c3f27a41
Revises: c7a4f2e19b35
Create Date: 2026-09-23 00:00:00.000000

추정매출 원천(OA-22175)의 요일·시간대·성별·연령대 분해 47컬럼을 1NF long으로 편 테이블을
추가한다 (설계서 §4-1). wide 53컬럼으로 두지 않는 근거는 ORM docstring 참조.

부모 `region_commerce_sales`와 복합 FK로 묶는다. 부모 PK가 정확히 같은 3컬럼이라 별도 UNIQUE
없이 PK를 그대로 참조할 수 있다.

autogenerate 결과에서 무관한 변경은 걷어냈다 — 이 브랜치의 alembic head와 실DB 리비전이
갈라져 있어(feature/analysis-api의 a1b2c3d4e5f6·b2c3d4e5f6a7가 DB에만 적용된 상태)
analysis_report·llm_usage 테이블 삭제, rag_chunk HNSW 인덱스 삭제, store 주소 2컬럼 삭제를
오탐한다. 남긴 것은 새 테이블과 조회 인덱스뿐이다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8b5c3f27a41"
down_revision: Union[str, Sequence[str], None] = "c7a4f2e19b35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "region_commerce_sales_breakdown",
        sa.Column("adstrd_code", sa.String(length=8), nullable=False),
        sa.Column("service_industry_code", sa.String(length=8), nullable=False),
        sa.Column("year_quarter", sa.String(length=5), nullable=False),
        sa.Column("dim_type", sa.String(length=8), nullable=False),
        sa.Column("dim_key", sa.String(length=8), nullable=False),
        sa.Column("region_code", sa.String(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("count", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["adstrd_code", "service_industry_code", "year_quarter"],
            [
                "region_commerce_sales.adstrd_code",
                "region_commerce_sales.service_industry_code",
                "region_commerce_sales.year_quarter",
            ],
            name="fk_region_commerce_sales_breakdown_parent",
        ),
        sa.ForeignKeyConstraint(["region_code"], ["region.region_code"]),
        sa.PrimaryKeyConstraint(
            "adstrd_code", "service_industry_code", "year_quarter", "dim_type", "dim_key"
        ),
    )
    op.create_index(
        "ix_region_commerce_sales_breakdown_region_industry",
        "region_commerce_sales_breakdown",
        ["region_code", "service_industry_code", "year_quarter", "dim_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_region_commerce_sales_breakdown_region_industry",
        table_name="region_commerce_sales_breakdown",
    )
    op.drop_table("region_commerce_sales_breakdown")
