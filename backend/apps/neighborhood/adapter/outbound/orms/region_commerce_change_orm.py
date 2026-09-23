from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장 (commerce breakdown 전례)
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
import apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionCommerceChangeOrm(OrmBase):
    """동별 상권 변화 지표 (OA-15575, 설계서 §4-6). 유일하게 넓은 형태다 — 반복 그룹이 없다.

    지표가 범주형(HH·HL·LH·LL)이라 숫자 값 컬럼에 담기지 않는다. `change_name`은 `change_code`에
    함수 종속이라 엄밀히 3NF 위반이지만, 코드 4종 고정 매핑이라 룩업 테이블의 편익이 없고 원천이
    두 컬럼을 같이 주므로 원본 보존 의미로 유지한다(§13이 허용하는 근거 있는 부분적 역정규화).

    `year_quarter`가 `seoul_commerce_change_baseline`을 참조한다 — 2NF로 떼어낸 서울 평균
    테이블을 ERD의 노드로 세우기 위한 엣지다. 적재 순서는 baseline이 먼저다.
    """

    __tablename__ = "region_commerce_change"
    __table_args__ = (
        Index("ix_region_commerce_change_region", "region_code", "year_quarter"),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(
        String(5), ForeignKey("seoul_commerce_change_baseline.year_quarter"), primary_key=True
    )
    change_code: Mapped[str | None] = mapped_column(String(2))  # HH | HL | LH | LL
    change_name: Mapped[str | None] = mapped_column(String(20))  # 정체 | 상권축소 | 상권확장 | 다이나믹
    operating_months: Mapped[float | None] = mapped_column(Float)
    closed_months: Mapped[float | None] = mapped_column(Float)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
