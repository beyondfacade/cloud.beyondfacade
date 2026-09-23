from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (childcare 전례)
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionCommerceSalesOrm(OrmBase):
    """서울 상권분석서비스 추정매출 — 행정동×업종×분기 (OA-22175, 2021Q1~2025Q4).

    industry_id를 저장하지 않는 근거: 업종 매핑 2건(cafe·gym)이 미확정이라 사실 테이블에 박으면
    매핑을 바꿀 때마다 34만 행 재적재가 필요하다. industry_source_code를 거쳐 조인한다 (설계서 §3-2).
    region_code는 조인 성능·ERD 연결(§13)을 위한 의도적 역정규화이며, 원천에만 있는 옛 행정동
    3개는 NULL로 남는다.
    """

    __tablename__ = "region_commerce_sales"
    __table_args__ = (
        Index(
            "ix_region_commerce_sales_region_industry",
            "region_code",
            "service_industry_code",
            "year_quarter",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)  # 원천 행정동_코드
    service_industry_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)  # '20251'
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    sales_amount: Mapped[int | None] = mapped_column(BigInteger)  # 당월_매출_금액
    sales_count: Mapped[int | None] = mapped_column(BigInteger)  # 당월_매출_건수
