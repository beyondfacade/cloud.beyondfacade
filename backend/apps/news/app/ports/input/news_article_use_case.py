"""Driving Port — news_article UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.news.app.dtos.news_article_dto import NewsArticleDto


class NewsArticleUseCase(ABC):
    @abstractmethod
    def myself(self) -> NewsArticleDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def ingest(self, keywords: list[str]) -> int:
        """키워드별 뉴스를 수집·중복제거 후 적재하고 신규 건수를 반환한다."""
