"""Driven Ports — news_article이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.news.domain.entities.news_article_entity import NewsArticle


class NewsArticleRepositoryPort(ABC):
    @abstractmethod
    def save_new(self, articles: list[NewsArticle]) -> int:
        """이미 존재하는 기사(article_id)는 건너뛰고 신규만 저장, 신규 건수 반환."""

    @abstractmethod
    def delete_published_before(self, cutoff: datetime) -> int:
        """게시 시각이 cutoff보다 이른 기사를 지우고 지운 건수를 반환한다."""


class NewsSearchGatewayPort(ABC):
    @abstractmethod
    def search(self, keyword: str) -> list[NewsArticle]:
        """키워드로 최신 뉴스를 검색해 엔티티로 반환한다."""
