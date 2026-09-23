from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionSpendingQuarterOrm(OrmBase):
    """지출 — 1NF long (OA-22166, 설계서 §4-5). 원본 1행 → total + 10종 = 11행.

    원천 컬럼 순서에서 `음식_지출_총금액`이 `기타_지출_총금액` 뒤에 온다. 게이트웨이가 순서가
    아니라 이름으로 찾는 이유이며, 뒤바뀌면 두 카테고리가 통째로 뒤집힌다(설계서 §3-7).
    """

    __tablename__ = "region_spending_quarter"
    __table_args__ = (
        Index(
            "ix_region_spending_quarter_region",
            "region_code",
            "year_quarter",
            "spending_category",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    spending_category: Mapped[str] = mapped_column(String(20), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    amount: Mapped[int | None] = mapped_column(BigInteger)  # 원
