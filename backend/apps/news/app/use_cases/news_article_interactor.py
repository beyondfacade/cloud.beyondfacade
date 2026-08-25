from datetime import datetime

from apps.news.app.dtos.news_article_dto import NewsArticleDto
from apps.news.app.ports.input.news_article_use_case import NewsArticleUseCase
from apps.news.app.ports.output.news_article_port import (
    NewsArticleRepositoryPort,
    NewsSearchGatewayPort,
)


class NewsArticleInteractor(NewsArticleUseCase):
    def __init__(
        self,
        repository: NewsArticleRepositoryPort,
        gateway: NewsSearchGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def myself(self) -> NewsArticleDto:
        return NewsArticleDto(
            article_id="myself",
            title="news BC 배선 검증",
            description="router → use_case → interactor 왕복 확인용 하드코딩 데이터",
            published_at=datetime(2026, 8, 25),
            url="https://example.com/myself",
            matched_keyword="myself",
        )

    def ingest(self, keywords: list[str]) -> int:
        inserted = 0
        for keyword in keywords:
            inserted += self._repository.save_new(self._gateway.search(keyword))
        return inserted
