"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.commerce.domain.entities.region_commerce_sales_entity import RegionCommerceSales


def to_row(entity: RegionCommerceSales) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "service_industry_code": entity.service_industry_code,
        "year_quarter": entity.year_quarter,
        "region_code": entity.region_code,
        "sales_amount": entity.sales_amount,
        "sales_count": entity.sales_count,
    }
