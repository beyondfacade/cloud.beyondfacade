from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (childcare 전례)
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionCommerceStoreOrm(OrmBase):
    """서울 상권분석서비스 점포 — 행정동×업종×분기 (OA-22172, 2021Q1~2025Q4).

    추정매출(63업종)보다 넓은 100업종을 담는다. 카드매출 추정이 안 되는 업종도 점포 수는 있다.
    """

    __tablename__ = "region_commerce_store"
    __table_args__ = (
        Index(
            "ix_region_commerce_store_region_industry",
            "region_code",
            "service_industry_code",
            "year_quarter",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    service_industry_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    store_count: Mapped[int | None]  # 점포_수
    similar_industry_store_count: Mapped[int | None]  # 유사_업종_점포_수
    open_rate: Mapped[float | None]  # 개업_율 (원천 표기 '율')
    open_store_count: Mapped[int | None]  # 개업_점포_수
    close_rate: Mapped[float | None]  # 폐업_률 (원천 표기 '률')
    close_store_count: Mapped[int | None]  # 폐업_점포_수
    franchise_store_count: Mapped[int | None]  # 프랜차이즈_점포_수
