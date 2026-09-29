from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (tobacco 전례)
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class AptTradeCountOrm(OrmBase):
    """아파트 매매 건수 — 수집 전용 보조 테이블 (erd.md 보조 테이블, 업종 특화 신호 설계서 §11).
    §13 연결 원칙: district FK로 마스터 허브에 연결. 법정동은 원천 문자열이라 FK 없음(행정동 배분은 verdict BC)."""

    __tablename__ = "apt_trade_count"

    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"), primary_key=True)
    legal_dong: Mapped[str] = mapped_column(String(40), primary_key=True)
    deal_ym: Mapped[str] = mapped_column(String(6), primary_key=True)
    trade_count: Mapped[int]
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
