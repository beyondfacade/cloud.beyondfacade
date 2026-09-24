"""region_commerce_sales/store tables + seoul_commercial industry source codes

Revision ID: c7a4f2e19b35
Revises: e2a08b1e8f19
Create Date: 2026-09-23 00:00:00.000000

서울 상권분석서비스 행정동 계열(OA-22175 추정매출 · OA-22172 점포) 적재용 테이블 2개와
업종 매핑 12행(source_system='seoul_commercial')을 추가한다.

매핑을 사실 테이블이 아니라 industry_source_code에 두는 근거: cafe·gym 2건의 매핑이 아직
미확정이라, 매핑을 바꿀 때 34만/70만 행을 재적재하지 않아도 되게 한다 (설계서 §3-2).
academy는 4:1이라 4행(CS200004 컴퓨터학원은 점포에만 있고 추정매출에는 없다).
childcare는 원천에 대응 업종이 없어 넣지 않는다.

autogenerate가 아니라 수기 작성이다 — 이 브랜치의 alembic head와 실DB 리비전이 갈라져 있어
(feature/analysis-api의 a1b2c3d4e5f6·b2c3d4e5f6a7가 DB에만 적용된 상태) autogenerate가
무관한 테이블 삭제를 오탐한다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a4f2e19b35"
down_revision: Union[str, Sequence[str], None] = "e2a08b1e8f19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (industry_id, 원천 서비스_업종_코드) — 설계서 §3-2 매핑표
_SOURCE_CODES = [
    ("academy", "CS200001"),  # 일반교습학원
    ("academy", "CS200002"),  # 외국어학원
    ("academy", "CS200003"),  # 예술학원
    ("academy", "CS200004"),  # 컴퓨터학원 (점포에만 존재, 추정매출 없음)
    ("billiard", "CS200016"),  # 당구장
    ("cafe", "CS100010"),  # 커피-음료 (휴게음식점 모집단과 정확히 겹치지 않음 — §3-2)
    ("convenience_store", "CS300002"),  # 편의점
    ("gym", "CS200024"),  # 스포츠클럽 (체력단련장업과 정의 차이 — §3-2)
    ("hair_salon", "CS200028"),  # 미용실
    ("karaoke", "CS200037"),  # 노래방
    ("pc_bang", "CS200019"),  # PC방
    ("real_estate", "CS200033"),  # 부동산중개업
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "region_commerce_sales",
        sa.Column("adstrd_code", sa.String(length=8), nullable=False),
        sa.Column("service_industry_code", sa.String(length=8), nullable=False),
        sa.Column("year_quarter", sa.String(length=5), nullable=False),
        sa.Column("region_code", sa.String(), nullable=True),
        sa.Column("sales_amount", sa.BigInteger(), nullable=True),
        sa.Column("sales_count", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["region_code"], ["region.region_code"]),
        sa.PrimaryKeyConstraint("adstrd_code", "service_industry_code", "year_quarter"),
    )
    op.create_index(
        "ix_region_commerce_sales_region_industry",
        "region_commerce_sales",
        ["region_code", "service_industry_code", "year_quarter"],
        unique=False,
    )
    op.create_table(
        "region_commerce_store",
        sa.Column("adstrd_code", sa.String(length=8), nullable=False),
        sa.Column("service_industry_code", sa.String(length=8), nullable=False),
        sa.Column("year_quarter", sa.String(length=5), nullable=False),
        sa.Column("region_code", sa.String(), nullable=True),
        sa.Column("store_count", sa.Integer(), nullable=True),
        sa.Column("similar_industry_store_count", sa.Integer(), nullable=True),
        sa.Column("open_rate", sa.Float(), nullable=True),
        sa.Column("open_store_count", sa.Integer(), nullable=True),
        sa.Column("close_rate", sa.Float(), nullable=True),
        sa.Column("close_store_count", sa.Integer(), nullable=True),
        sa.Column("franchise_store_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["region_code"], ["region.region_code"]),
        sa.PrimaryKeyConstraint("adstrd_code", "service_industry_code", "year_quarter"),
    )
    op.create_index(
        "ix_region_commerce_store_region_industry",
        "region_commerce_store",
        ["region_code", "service_industry_code", "year_quarter"],
        unique=False,
    )
    # 빈 DB(테스트 DB)엔 industry 행이 없어 FK 위반으로 전체 롤백된다 — 마스터는 seed_master CLI 몫이라 건너뛴다
    if op.get_bind().execute(sa.text("select count(*) from industry")).scalar() == 0:
        return
    op.bulk_insert(
        sa.table(
            "industry_source_code",
            sa.column("industry_id", sa.String),
            sa.column("source_system", sa.String),
            sa.column("code", sa.String),
        ),
        [
            {"industry_id": industry_id, "source_system": "seoul_commercial", "code": code}
            for industry_id, code in _SOURCE_CODES
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM industry_source_code WHERE source_system = 'seoul_commercial'")
    op.drop_index("ix_region_commerce_store_region_industry", table_name="region_commerce_store")
    op.drop_table("region_commerce_store")
    op.drop_index("ix_region_commerce_sales_region_industry", table_name="region_commerce_sales")
    op.drop_table("region_commerce_sales")
