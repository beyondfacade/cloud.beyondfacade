"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.news.adapter.inbound.api.schemas.news_article_schema import NewsArticleResponse
from apps.news.app.dtos.news_article_dto import NewsArticleDto


def to_response(dto: NewsArticleDto) -> NewsArticleResponse:
    return NewsArticleResponse(**asdict(dto))
