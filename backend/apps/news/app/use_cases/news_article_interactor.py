from datetime import datetime, timedelta

from apps.news.app.dtos.news_article_dto import NewsArticleDto
from apps.news.app.ports.input.news_article_use_case import NewsArticleUseCase
from apps.news.app.ports.output.news_article_port import (
    NewsArticleRepositoryPort,
    NewsSearchGatewayPort,
)

# 네이버 검색 API 특약 2.4 — 검색 결과는 서버 이력 조회 목적으로 최대 21일만 보관한다.
RETENTION_DAYS = 21


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

    def purge(self, now: datetime) -> int:
        return self._repository.delete_published_before(now - timedelta(days=RETENTION_DAYS))
