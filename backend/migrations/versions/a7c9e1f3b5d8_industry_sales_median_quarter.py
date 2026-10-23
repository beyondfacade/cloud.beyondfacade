"""업종×분기 서울 점포당 매출 중앙값 — industry_sales_median_quarter (집계 계층) + 첫 채우기

재무 프리필이 요청마다 다시 계산하던 값(11차 부하 테스트 DB 시간의 대부분)을 미리 계산해 둔다.
채우기 식은 apps/metric/adapter/outbound/repositories/industry_sales_median_repository.py와 같다 —
마이그레이션은 앱 코드를 import하지 않으므로 복사해 둔다. 이후 갱신은 매일 새벽 build_sales_median.

Revision ID: a7c9e1f3b5d8
Revises: f6a8b1c3d5e7
Create Date: 2026-10-23
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c9e1f3b5d8"
down_revision: Union[str, Sequence[str], None] = "f6a8b1c3d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industry_sales_median_quarter",
        sa.Column("industry_id", sa.String(), sa.ForeignKey("industry.industry_id"), primary_key=True),
        sa.Column("year_quarter", sa.String(5), primary_key=True),
        sa.Column("median_quarterly_sales_per_store", sa.Float(), nullable=False),
        sa.Column("region_count", sa.Integer(), nullable=False),
    )
    op.execute(
        """
        INSERT INTO industry_sales_median_quarter
            (industry_id, year_quarter, median_quarterly_sales_per_store, region_count)
        SELECT industry_id, year_quarter, percentile_cont(0.5) WITHIN GROUP (ORDER BY per_store), count(*)
        FROM (
            SELECT code.industry_id, sales.year_quarter, sales.region_code,
                   sum(sales.sales_amount) / sum(store.store_count) AS per_store
            FROM region_commerce_sales AS sales
            JOIN region_commerce_store AS store
              ON store.adstrd_code = sales.adstrd_code
             AND store.service_industry_code = sales.service_industry_code
             AND store.year_quarter = sales.year_quarter
            JOIN industry_source_code AS code
              ON code.code = sales.service_industry_code AND code.source_system = 'seoul_commercial'
            WHERE sales.sales_amount IS NOT NULL AND store.store_count IS NOT NULL
            GROUP BY code.industry_id, sales.year_quarter, sales.region_code
            HAVING sum(store.store_count) > 0
        ) AS per_region
        GROUP BY industry_id, year_quarter
        """
    )


def downgrade() -> None:
    op.drop_table("industry_sales_median_quarter")
