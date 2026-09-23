"""neighborhood 동네 맥락 7종 테이블

Revision ID: f3c9a1d47b62
Revises: d8b5c3f27a41
Create Date: 2026-09-23 00:00:00.000000

서울 상권분석서비스 동네 맥락 7종(유동인구·직장인구·상주인구·집객시설·소비·아파트·상권변화)을
담는 테이블을 추가한다 (설계서 `docs/superpowers/specs/2026-09-23-neighborhood-bc-design.md` §4).

- 긴 형태 5종(footfall·population·household·facility·spending)은 원본 wide 컬럼을 1NF long으로
  편 것이다. 축이 늘 때마다 DDL이 필요한 문제를 피한다
- `region_housing_average_quarter`는 §4-3 미확정 1의 결정 결과다. 세대 수(개수)와 평균 면적(㎡)·
  평균 시가(원)는 단위가 달라 한 값 컬럼에 담지 않는다
- `seoul_commerce_change_baseline`은 §3-5의 2NF 분리 결과다. 서울 평균 2컬럼이 행정동이 아니라
  분기에만 의존한다. 분기만 키라 그대로 두면 고립되므로 `region_commerce_change.year_quarter`가
  이를 FK로 참조한다 — 따라서 **적재 순서는 baseline이 먼저다**

autogenerate 결과에서 무관한 변경은 걷어냈다 — 이 브랜치의 alembic head와 실DB 리비전이
갈라져 있어(feature/analysis-api의 a1b2c3d4e5f6·b2c3d4e5f6a7가 DB에만 적용된 상태) 다음 6건을
오탐한다: analysis_report·llm_usage 테이블 삭제, rag_chunk HNSW 인덱스 삭제, store 지오코딩
인덱스 삭제, store 주소 2컬럼 삭제. 남긴 것은 새 테이블 8개와 조회 인덱스 7개뿐이다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3c9a1d47b62"
down_revision: Union[str, Sequence[str], None] = "d8b5c3f27a41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('seoul_commerce_change_baseline',
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('seoul_operating_months', sa.Float(), nullable=True),
    sa.Column('seoul_closed_months', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('year_quarter')
    )
    op.create_table('region_commerce_change',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('change_code', sa.String(length=2), nullable=True),
    sa.Column('change_name', sa.String(length=20), nullable=True),
    sa.Column('operating_months', sa.Float(), nullable=True),
    sa.Column('closed_months', sa.Float(), nullable=True),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.ForeignKeyConstraint(['year_quarter'], ['seoul_commerce_change_baseline.year_quarter'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter')
    )
    op.create_index('ix_region_commerce_change_region', 'region_commerce_change', ['region_code', 'year_quarter'], unique=False)
    op.create_table('region_facility_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('facility_type', sa.String(length=20), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('facility_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter', 'facility_type')
    )
    op.create_index('ix_region_facility_quarter_region', 'region_facility_quarter', ['region_code', 'year_quarter', 'facility_type'], unique=False)
    op.create_table('region_footfall_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('dim_type', sa.String(length=16), nullable=False),
    sa.Column('dim_key', sa.String(length=16), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('headcount', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter', 'dim_type', 'dim_key')
    )
    op.create_index('ix_region_footfall_quarter_region', 'region_footfall_quarter', ['region_code', 'year_quarter', 'dim_type'], unique=False)
    op.create_table('region_household_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('dim_type', sa.String(length=20), nullable=False),
    sa.Column('dim_key', sa.String(length=16), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('value', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter', 'dim_type', 'dim_key')
    )
    op.create_index('ix_region_household_quarter_region', 'region_household_quarter', ['region_code', 'year_quarter', 'dim_type'], unique=False)
    op.create_table('region_housing_average_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('avg_area_m2', sa.Float(), nullable=True),
    sa.Column('avg_price', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter')
    )
    op.create_index('ix_region_housing_average_quarter_region', 'region_housing_average_quarter', ['region_code', 'year_quarter'], unique=False)
    op.create_table('region_population_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('population_type', sa.String(length=8), nullable=False),
    sa.Column('dim_type', sa.String(length=16), nullable=False),
    sa.Column('dim_key', sa.String(length=16), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('headcount', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter', 'population_type', 'dim_type', 'dim_key')
    )
    op.create_index('ix_region_population_quarter_region', 'region_population_quarter', ['region_code', 'year_quarter', 'population_type', 'dim_type'], unique=False)
    op.create_table('region_spending_quarter',
    sa.Column('adstrd_code', sa.String(length=8), nullable=False),
    sa.Column('year_quarter', sa.String(length=5), nullable=False),
    sa.Column('spending_category', sa.String(length=20), nullable=False),
    sa.Column('region_code', sa.String(), nullable=True),
    sa.Column('amount', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('adstrd_code', 'year_quarter', 'spending_category')
    )
    op.create_index('ix_region_spending_quarter_region', 'region_spending_quarter', ['region_code', 'year_quarter', 'spending_category'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_region_spending_quarter_region', table_name='region_spending_quarter')
    op.drop_table('region_spending_quarter')
    op.drop_index('ix_region_population_quarter_region', table_name='region_population_quarter')
    op.drop_table('region_population_quarter')
    op.drop_index('ix_region_housing_average_quarter_region', table_name='region_housing_average_quarter')
    op.drop_table('region_housing_average_quarter')
    op.drop_index('ix_region_household_quarter_region', table_name='region_household_quarter')
    op.drop_table('region_household_quarter')
    op.drop_index('ix_region_footfall_quarter_region', table_name='region_footfall_quarter')
    op.drop_table('region_footfall_quarter')
    op.drop_index('ix_region_facility_quarter_region', table_name='region_facility_quarter')
    op.drop_table('region_facility_quarter')
    op.drop_index('ix_region_commerce_change_region', table_name='region_commerce_change')
    op.drop_table('region_commerce_change')
    op.drop_table('seoul_commerce_change_baseline')
