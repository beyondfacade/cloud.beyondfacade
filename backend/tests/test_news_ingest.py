"""news ingest 검증 — Fake 게이트웨이(경계 모킹) + 실제 Repository/DB로 중복 제거 적재."""

from datetime import datetime

from sqlalchemy import delete, func, select

from apps.news.adapter.outbound.orms.news_article_orm import NewsArticleOrm
from apps.news.adapter.outbound.repositories.news_article_repository import (
    SqlAlchemyNewsArticleRepository,
)
from apps.news.app.ports.output.news_article_port import NewsSearchGatewayPort
from apps.news.app.use_cases.news_article_interactor import NewsArticleInteractor
from apps.news.domain.entities.news_article_entity import NewsArticle
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-ingest-"


def _article(n: int, keyword: str) -> NewsArticle:
    return NewsArticle(
        article_id=f"{_TEST_PREFIX}{n}",
        title=f"기사 {n}",
        description=f"발췌 {n}",
        published_at=datetime(2026, 8, 25, 12, 0),
        url=f"https://example.com/{_TEST_PREFIX}{n}",
        matched_keyword=keyword,
    )


class FakeGateway(NewsSearchGatewayPort):
    def search(self, keyword: str) -> list[NewsArticle]:
        # 두 키워드가 기사 2번을 공유 — 배치 내 중복 상황 재현
        if keyword == "키워드A":
            return [_article(1, keyword), _article(2, keyword)]
        return [_article(2, keyword), _article(3, keyword)]


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(NewsArticleOrm).where(NewsArticleOrm.article_id.like(f"{_TEST_PREFIX}%"))
        )


def test_ingest_dedups_within_batch_and_across_runs():
    _cleanup()
    interactor = NewsArticleInteractor(
        repository=SqlAlchemyNewsArticleRepository(), gateway=FakeGateway()
    )

    first = interactor.ingest(["키워드A", "키워드B"])
    assert first == 3  # 기사 4건 중 중복 1건 제외

    second = interactor.ingest(["키워드A", "키워드B"])
    assert second == 0  # 재실행 시 전부 기존 기사

    with session_scope() as session:
        stored = session.execute(
            select(func.count())
            .select_from(NewsArticleOrm)
            .where(NewsArticleOrm.article_id.like(f"{_TEST_PREFIX}%"))
        ).scalar()
    assert stored == 3
    _cleanup()
