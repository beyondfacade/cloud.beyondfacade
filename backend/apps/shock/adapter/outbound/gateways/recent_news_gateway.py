"""Driven Adapter — news BC 검색 게이트웨이로 최신 기사를 찾아 헤드라인만 남긴다 (cross-BC 접근은 여기서만)."""

from apps.news.app.ports.output.news_article_port import NewsSearchGatewayPort
from apps.shock.app.ports.output.event_analog_port import RecentNewsPort
from apps.shock.domain.value_objects.news_headline import NewsHeadline


class RecentNewsGateway(RecentNewsPort):
    def __init__(self, search: NewsSearchGatewayPort) -> None:
        self._search = search

    def latest(self, keyword: str) -> list[NewsHeadline]:
        return [NewsHeadline(a.title, a.published_at, a.url) for a in self._search.search(keyword)]
