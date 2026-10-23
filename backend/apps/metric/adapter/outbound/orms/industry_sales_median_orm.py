from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class IndustrySalesMedianOrm(OrmBase):
    """업종×분기 서울 점포당 매출 중앙값 — 상권 원천에서 배치 재생성 (역정규화 허용 계층, docs/erd.md).

    재무 프리필이 요청마다 다시 계산하던 값이다. 업종×분기에만 달려 있어 미리 계산해 둔다 — 11차 부하
    테스트에서 이 계산이 DB 시간의 대부분이었다(serverplan §21-10·§21-12).
    """

    __tablename__ = "industry_sales_median_quarter"

    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)  # 원천 기준_년분기_코드 '20254'
    # 동마다 (분기 매출 합 ÷ 점포 합)을 낸 값의 서울 중앙값 — 분기 합 단위(원천 `당월_매출_금액`은 분기 합)
    median_quarterly_sales_per_store: Mapped[float]
    region_count: Mapped[int]  # 중앙값에 들어간 동 수 (검수용)
