"""분해 적재 결과 DTO — 매출·점포와 형태가 같아 sales DTO를 단일 원천으로 재사용한다."""

from apps.commerce.app.dtos.region_commerce_sales_dto import CommerceIngestResultDto

__all__ = ["CommerceIngestResultDto"]
