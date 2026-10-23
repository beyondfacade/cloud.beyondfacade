"""업종×분기 서울 점포당 매출 중앙값 — DB 안에서 한 번에 다시 만든다.

427개 동 × 분기 집계라 원천을 파이썬으로 끌어오지 않는다. 식은 재무 프리필이 요청마다 하던 계산과 같다:
업종에 붙은 상권 원천 코드(`seoul_commercial`)를 동 안에서 합쳐 (분기 매출 합 ÷ 점포 합), 점포 합이 0인 동과
매출·점포가 비어 있는 행은 빼고, 동별 값의 `percentile_cont(0.5)`. 마이그레이션의 첫 채우기도 같은 식이다.
지우고 다시 넣으므로 업종-원천 코드 매핑이 바뀌어 사라진 조합도 남지 않는다.
"""

from sqlalchemy import text

from apps.metric.app.ports.output.industry_sales_median_port import IndustrySalesMedianRepositoryPort
from core.matrix.grid_oracle_database_manager import session_scope

_REBUILD = text(
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


class SqlAlchemyIndustrySalesMedianRepository(IndustrySalesMedianRepositoryPort):
    def rebuild(self) -> int:
        with session_scope() as session:
            session.execute(text("DELETE FROM industry_sales_median_quarter"))
            return session.execute(_REBUILD).rowcount
