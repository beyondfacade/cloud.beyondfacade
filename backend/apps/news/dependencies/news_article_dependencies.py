"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.news.adapter.outbound.gateways.naver_news_gateway import NaverNewsGateway
from apps.news.adapter.outbound.repositories.news_article_repository import (
    SqlAlchemyNewsArticleRepository,
)
from apps.news.app.ports.input.news_article_use_case import NewsArticleUseCase
from apps.news.app.use_cases.news_article_interactor import NewsArticleInteractor


def get_news_article_use_case() -> NewsArticleUseCase:
    return NewsArticleInteractor(
        repository=SqlAlchemyNewsArticleRepository(),
        gateway=NaverNewsGateway(),
    )
