"""네이버 검색 API(NAVER API HUB) Driven Adapter — 뉴스 검색.

docs/api.md ⑩: 엔드포인트·헤더는 2026-07-31 API HUB 이관 이후 스펙.
"""

import hashlib
import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

from apps.news.app.ports.output.news_article_port import NewsSearchGatewayPort
from apps.news.domain.entities.news_article_entity import NewsArticle
from core.matrix.grid_keymaker_secret_manager import get_settings

_ENDPOINT = "https://naverapihub.apigw.ntruss.com/search/v1/news"
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return html.unescape(_TAG_PATTERN.sub("", text)).strip()


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:20]


class NaverNewsGateway(NewsSearchGatewayPort):
    def __init__(self, display: int = 100) -> None:
        self._display = display

    def search(self, keyword: str) -> list[NewsArticle]:
        settings = get_settings()
        response = httpx.get(
            _ENDPOINT,
            params={"query": keyword, "display": self._display, "sort": "date"},
            headers={
                "X-NCP-APIGW-API-KEY-ID": settings.naver_ncp_api_key_id,
                "X-NCP-APIGW-API-KEY": settings.naver_ncp_api_key,
            },
            timeout=15,
        )
        response.raise_for_status()

        articles = []
        for item in response.json()["items"]:
            url = item["originallink"] or item["link"]
            articles.append(
                NewsArticle(
                    article_id=_article_id(url),
                    title=_clean(item["title"]),
                    description=_clean(item["description"]),
                    published_at=self._parse_pubdate(item["pubDate"]),
                    url=url,
                    matched_keyword=keyword,
                )
            )
        return articles

    @staticmethod
    def _parse_pubdate(value: str) -> datetime:
        return parsedate_to_datetime(value).replace(tzinfo=None)
