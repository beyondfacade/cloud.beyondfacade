from fastapi import APIRouter, Depends

from apps.news.adapter.inbound.api.schemas.news_article_schema import NewsArticleResponse
from apps.news.adapter.inbound.mappers.news_article_mapper import to_response
from apps.news.app.ports.input.news_article_use_case import NewsArticleUseCase
from apps.news.dependencies.news_article_dependencies import get_news_article_use_case

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/myself", response_model=NewsArticleResponse)
def myself(
    use_case: NewsArticleUseCase = Depends(get_news_article_use_case),
) -> NewsArticleResponse:
    return to_response(use_case.myself())
