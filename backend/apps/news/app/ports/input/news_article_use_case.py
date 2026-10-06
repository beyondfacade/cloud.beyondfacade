"""Driving Port — news_article UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.news.app.dtos.news_article_dto import NewsArticleDto


class NewsArticleUseCase(ABC):
    @abstractmethod
    def myself(self) -> NewsArticleDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def ingest(self, keywords: list[str]) -> int:
        """키워드별 뉴스를 수집·중복제거 후 적재하고 신규 건수를 반환한다."""

    @abstractmethod
    def purge(self, now: datetime) -> int:
        """보관 기한(게시 후 21일)이 지난 기사를 지우고 지운 건수를 반환한다."""
