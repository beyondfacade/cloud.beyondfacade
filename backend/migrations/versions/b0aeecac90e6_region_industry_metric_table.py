"""region_industry_metric table

Revision ID: b0aeecac90e6
Revises: 43367fbe8af0
Create Date: 2026-09-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0aeecac90e6'
down_revision: Union[str, Sequence[str], None] = '43367fbe8af0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('region_industry_metric',
    sa.Column('region_code', sa.String(), nullable=False),
    sa.Column('industry_id', sa.String(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('store_count', sa.Integer(), nullable=False),
    sa.Column('open_count', sa.Integer(), nullable=False),
    sa.Column('close_count', sa.Integer(), nullable=False),
    sa.Column('closure_rate', sa.Float(), nullable=True),
    sa.Column('growth_rate', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['industry_id'], ['industry.industry_id'], ),
    sa.ForeignKeyConstraint(['region_code'], ['region.region_code'], ),
    sa.PrimaryKeyConstraint('region_code', 'industry_id', 'year')
    )
    op.create_index('ix_region_industry_metric_industry_year', 'region_industry_metric', ['industry_id', 'year'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_region_industry_metric_industry_year', table_name='region_industry_metric')
    op.drop_table('region_industry_metric')
