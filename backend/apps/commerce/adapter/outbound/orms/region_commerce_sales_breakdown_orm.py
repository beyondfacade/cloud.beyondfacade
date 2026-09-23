from sqlalchemy import BigInteger, ForeignKey, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장 (childcare 전례)
import apps.commerce.adapter.outbound.orms.region_commerce_sales_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionCommerceSalesBreakdownOrm(OrmBase):
    """추정매출 요일·시간대·성별·연령대 분해 — 1NF long 테이블 (OA-22175, 설계서 §4-1).

    wide 47컬럼으로 두지 않는 근거: 축이 늘어날 때마다 DDL이 필요하고, "시간대별 상위 3구간"
    같은 질의가 47개 컬럼 UNION이 된다. (dim_type, dim_key)를 값으로 내리면 축 추가가 적재만으로
    끝난다.

    부모 `region_commerce_sales`와 복합 FK로 묶는다. 부모 PK가 정확히 같은 3컬럼이라 별도
    UNIQUE 없이 PK를 그대로 참조할 수 있고, 총액 없는 분해 행이라는 모순 상태가 DB에서 막힌다.
    `region_code`는 부모를 거치지 않고 동 단위로 바로 조회하기 위한 의도적 역정규화이며
    (ERD §13 엣지 + 조인 성능), 원천에만 있는 옛 행정동 3개는 NULL로 남는다.
    """

    __tablename__ = "region_commerce_sales_breakdown"
    __table_args__ = (
        ForeignKeyConstraint(
            ["adstrd_code", "service_industry_code", "year_quarter"],
            [
                "region_commerce_sales.adstrd_code",
                "region_commerce_sales.service_industry_code",
                "region_commerce_sales.year_quarter",
            ],
            name="fk_region_commerce_sales_breakdown_parent",
        ),
        Index(
            "ix_region_commerce_sales_breakdown_region_industry",
            "region_code",
            "service_industry_code",
            "year_quarter",
            "dim_type",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    service_industry_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)  # '20251'
    dim_type: Mapped[str] = mapped_column(String(8), primary_key=True)  # 최장 'weekpart'
    dim_key: Mapped[str] = mapped_column(String(8), primary_key=True)  # 최장 'weekday'/'60_over'
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    amount: Mapped[int | None] = mapped_column(BigInteger)  # 구간 매출 금액
    count: Mapped[int | None] = mapped_column(BigInteger)  # 구간 매출 건수
