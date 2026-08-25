from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class NewsArticleOrm(OrmBase):
    """뉴스 기사 — 제목·발췌·링크만 저장 (본문 금지). event_id FK는 shock_event BC 생성 시 추가."""

    __tablename__ = "news_article"

    article_id: Mapped[str] = mapped_column(primary_key=True)  # sha1(url) 앞 20자리
    title: Mapped[str]
    description: Mapped[str]
    published_at: Mapped[datetime]
    url: Mapped[str] = mapped_column(unique=True)
    matched_keyword: Mapped[str]
    press: Mapped[str | None]
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
