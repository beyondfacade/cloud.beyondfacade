from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class SeoulCommerceChangeBaselineOrm(OrmBase):
    """분기별 서울 전체 평균 — 2NF 분리 결과 (OA-15575, 설계서 §3-5 · §4-7). 22행.

    원천이 425개 동 행마다 같은 값을 반복해 실어 보낸다(22개 분기 전부에서 고유값 1개 실측).
    행정동이 아니라 분기에만 의존하는 부분 함수 종속이라 떼어냈다. 분기만 키라 그대로 두면
    고립되므로 `region_commerce_change.year_quarter`가 이 테이블을 참조한다(§13).
    """

    __tablename__ = "seoul_commerce_change_baseline"

    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    seoul_operating_months: Mapped[float | None] = mapped_column(Float)
    seoul_closed_months: Mapped[float | None] = mapped_column(Float)
