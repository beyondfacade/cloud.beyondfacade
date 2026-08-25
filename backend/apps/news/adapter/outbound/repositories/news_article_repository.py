from sqlalchemy import select

from apps.news.adapter.outbound.orm_mappers.news_article_orm_mapper import to_orm
from apps.news.adapter.outbound.orms.news_article_orm import NewsArticleOrm
from apps.news.app.ports.output.news_article_port import NewsArticleRepositoryPort
from apps.news.domain.entities.news_article_entity import NewsArticle
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyNewsArticleRepository(NewsArticleRepositoryPort):
    def save_new(self, articles: list[NewsArticle]) -> int:
        if not articles:
            return 0
        with session_scope() as session:
            existing = set(
                session.execute(
                    select(NewsArticleOrm.article_id).where(
                        NewsArticleOrm.article_id.in_([a.article_id for a in articles])
                    )
                ).scalars()
            )
            new_articles = {
                a.article_id: a for a in articles if a.article_id not in existing
            }  # dict — 같은 배치 안의 중복(여러 키워드에 걸린 기사)도 제거
            for article in new_articles.values():
                session.add(to_orm(article))
            return len(new_articles)
