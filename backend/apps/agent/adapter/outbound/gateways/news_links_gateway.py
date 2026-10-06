"""Driven Adapter — news BC 기사 원문 링크 (cross-BC 접근은 이 파일 안에서만). 발췌는 내보내지 않는다."""

from datetime import datetime, timedelta

from sqlalchemy import or_, select

from apps.agent.app.ports.output.agent_port import NewsLinksPort
from apps.news.adapter.outbound.orms.news_article_orm import NewsArticleOrm
from apps.news.app.use_cases.news_article_interactor import RETENTION_DAYS
from core.matrix.grid_oracle_database_manager import session_scope


class NewsLinksGateway(NewsLinksPort):
    def mentioning(self, name: str, limit: int) -> list[dict]:
        N, pattern = NewsArticleOrm, f"%{name}%"
        with session_scope() as session:
            rows = session.execute(
                select(N.title, N.url, N.published_at, N.press)
                .where(
                    N.published_at >= datetime.now() - timedelta(days=RETENTION_DAYS),
                    or_(N.title.like(pattern), N.description.like(pattern)),
                )
                .order_by(N.published_at.desc())
                .limit(limit)
            ).all()
        return [
            {"title": title, "url": url, "published_at": published_at.date().isoformat(), "press": press}
            for title, url, published_at, press in rows
        ]
