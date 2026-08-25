"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.news.adapter.outbound.orms.news_article_orm import NewsArticleOrm
from apps.news.domain.entities.news_article_entity import NewsArticle


def to_orm(entity: NewsArticle) -> NewsArticleOrm:
    return NewsArticleOrm(
        article_id=entity.article_id,
        title=entity.title,
        description=entity.description,
        published_at=entity.published_at,
        url=entity.url,
        matched_keyword=entity.matched_keyword,
        press=entity.press,
        region_code=entity.region_code,
    )


def to_entity(orm: NewsArticleOrm) -> NewsArticle:
    return NewsArticle(
        article_id=orm.article_id,
        title=orm.title,
        description=orm.description,
        published_at=orm.published_at,
        url=orm.url,
        matched_keyword=orm.matched_keyword,
        press=orm.press,
        region_code=orm.region_code,
    )
